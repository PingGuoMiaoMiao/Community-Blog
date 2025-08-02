#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path
from typing import List, Dict
from translator import MarkdownTranslator
from github import Github
from git import Repo
import logging
from datetime import datetime
import shutil

# 修复模块导入问题
sys.path.append(str(Path(__file__).parent.resolve()))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationBot:
    def __init__(self):
        self.args = self.parse_args()
        self.api_key = os.getenv("API_KEY")
        if not self.api_key:
            logger.error("Missing API_KEY environment variable")
            sys.exit(1)
        self.translator = MarkdownTranslator(self.api_key)
        self.run_id = os.getenv("GITHUB_RUN_ID", "manual-run")
        
        # 初始化Git仓库
        try:
            self.repo = Repo(".")
            logger.info(f"Initialized Git repo at {self.repo.working_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize Git repo: {str(e)}")
            if self.args.dry_run:
                logger.warning("Continuing in dry-run mode without Git")
            else:
                sys.exit(1)

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Automated Markdown Translation Bot')
        parser.add_argument("--source-dir", default="trees", help="Source directory with Chinese markdown")
        parser.add_argument("--target-dir", default="trees_en", help="Target directory for English translations")
        parser.add_argument("--pr-reviewers", default="", help="Comma-separated GitHub reviewers")
        parser.add_argument("--dry-run", action="store_true", help="Run without pushing changes")
        return parser.parse_args()

    def run(self):
        try:
            logger.info(f"Starting translation run {self.run_id}")
            
            # 阶段1：检测和验证变更
            changed_files = self.get_changed_files()
            if not changed_files:
                logger.info("No changed Markdown files detected")
                return
            
            # 阶段2：执行翻译
            stats = self.execute_translation(changed_files)
            
            # 阶段3：提交和创建PR
            if self.args.dry_run:
                logger.info("⚠️ Dry run mode activated. No changes will be committed.")
                logger.info(f"Would create PR for {len(changed_files)} files")
            else:
                self.create_versioned_pr(changed_files, stats)
            
            logger.info(f"Translation completed successfully")
            
        except Exception as e:
            logger.error(f"Translation pipeline failed: {str(e)}", exc_info=True)
            sys.exit(1)

    def get_changed_files(self) -> List[str]:
        """识别已修改/添加的markdown文件"""
        changed = []
        source_path = Path(self.args.source_dir).absolute()
        
        try:
            # 获取所有未暂存的变更
            diff_result = self.repo.index.diff(None)
            
            for diff_item in diff_result:
                file_path = diff_item.a_path
                
                # 只处理.md文件
                if file_path and file_path.endswith('.md'):
                    abs_path = (self.repo.working_dir / file_path).absolute()
                    
                    # 验证文件在源目录中
                    try:
                        rel_path = abs_path.relative_to(source_path)
                        if not str(rel_path).startswith('..'):
                            changed.append(str(abs_path))
                    except ValueError:
                        continue
        except Exception as e:
            logger.error(f"Failed to detect changed files: {str(e)}")
        
        if changed:
            logger.info(f"Detected {len(changed)} changed files")
            sample_files = "\n".join([f"  - {Path(f).relative_to(self.args.source_dir)}" for f in changed[:3]])
            if len(changed) > 3:
                sample_files += f"\n  - ...(+{len(changed)-3} more)"
            logger.info(f"Changed files:\n{sample_files}")
        else:
            logger.warning("No valid markdown changes detected")
        return changed

    def execute_translation(self, files: List[str]) -> Dict[str, int]:
        """使用结构保留执行批量翻译"""
        # 确保输出目录存在
        output_dir = Path(self.args.target_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取相对路径用于处理
        rel_files = [str(Path(f).relative_to(self.args.source_dir)) for f in files]
        
        logger.info(f"Starting translation of {len(files)} files to {output_dir}...")
        
        # 调用翻译器
        stats = self.translator.batch_translate(
            input_dir=self.args.source_dir,
            output_dir=self.args.target_dir,
            specific_files=rel_files
        )
        
        if stats['success'] == 0:
            raise Exception("All translations failed")
            
        logger.info(f"Translation results: ✅ {stats['success']} succeeded, ❌ {stats['failed']} failed")
        return stats

    def create_versioned_pr(self, changed_files: List[str], stats: Dict[str, int]):
        """提交变更并创建带版本的PR"""
        # 配置Git身份
        self.repo.git.config("user.name", "Translation Bot")
        self.repo.git.config("user.email", "translation-bot@users.noreply.github.com")
        
        # 创建带版本的branch
        branch_name = f"translation-{self.run_id}"
        logger.info(f"Creating branch {branch_name}")
        
        # 添加所有更改
        self.repo.git.add(A=True)
        
        # 创建提交
        commit_msg = f"""feat(translation): batch update {self.run_id}

Files processed:
- Success: {stats['success']}
- Failed: {stats['failed']}
"""
        self.repo.index.commit(commit_msg)
        logger.info("Changes committed")
        
        # 推送到branch
        origin = self.repo.remote(name='origin')
        origin.push(refspec=f"HEAD:{branch_name}", force=True)
        logger.info(f"Pushed to {branch_name}")
        
        # 创建PR
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise Exception("Missing GITHUB_TOKEN")
            
        g = Github(github_token)
        repo_name = os.getenv("GITHUB_REPOSITORY")
        if not repo_name:
            raise Exception("Missing GITHUB_REPOSITORY")
            
        repo = g.get_repo(repo_name)
        
        pr_title = f"[Bot] Translation Updates ({self.run_id})"
        pr_body = self.generate_pr_body(changed_files, stats)
        
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base="main",
            labels=["translation", "needs-review"]
        )
        
        # 设置审阅者
        if self.args.pr_reviewers:
            reviewers = [r.strip() for r in self.args.pr_reviewers.split(",") if r.strip()]
            logger.info(f"Adding reviewers: {', '.join(reviewers)}")
            pr.create_review_request(reviewers=reviewers)
        
        logger.info(f"Created PR #{pr.number}: {pr.html_url}")

    def generate_pr_body(self, files: List[str], stats: Dict[str, int]) -> str:
        """生成完整的PR描述"""
        sample_files = "\n".join(f"- `{Path(f).relative_to(self.args.source_dir)}`" for f in files[:5])
        if len(files) > 5:
            sample_files += f"\n- ...(+{len(files)-5} more files)"
        
        return f"""
## Translation Report (Run {self.run_id})

### Statistics
✅ Successfully translated: **{stats['success']} files**  
❌ Failed translations: **{stats['failed']} files**

### Changed Files
{sample_files}

### Verification Checklist
1. [ ] Markdown formatting preserved
2. [ ] Code blocks unchanged
3. [ ] Technical terms accurate
4. [ ] URLs functional

### Output Structure
> Automatically generated by translation pipeline
"""

    def get_directory_tree(self, path: Path, max_depth: int = 3) -> str:
        """获取目录结构文本表示"""
        try:
            lines = []
            prefix = ""
            
            for entry in path.iterdir():
                if entry.is_dir():
                    lines.append(f"{prefix}├── {entry.name}/")
                    self.walk_directory(entry, lines, prefix + "│   ", max_depth-1)
                else:
                    lines.append(f"{prefix}├── {entry.name}")
            
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Failed to generate tree: {str(e)}")
            return "Could not generate directory tree"
    
    def walk_directory(self, path: Path, lines: list, prefix: str, depth: int):
        if depth <= 0:
            return
            
        entries = list(path.iterdir())
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            
            if entry.is_dir():
                lines.append(f"{prefix}{'└──' if is_last else '├──'} {entry.name}/")
                if depth > 1:
                    self.walk_directory(entry, lines, new_prefix, depth-1)
            else:
                lines.append(f"{prefix}{'└──' if is_last else '├──'} {entry.name}")

if __name__ == "__main__":
    try:
        TranslationBot().run()
    except Exception as e:
        logger.error(f"Fatal error in translation bot: {str(e)}", exc_info=True)
        sys.exit(1)