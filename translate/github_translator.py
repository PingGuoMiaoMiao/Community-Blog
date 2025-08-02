import argparse
import os
from pathlib import Path
from typing import List, Dict
from translator import MarkdownTranslator
from github import Github
from git import Repo
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationManager:
    def __init__(self):
        self.args = self.parse_args()
        self.translator = MarkdownTranslator(os.getenv("API_KEY"))
        self.repo = Repo(".")
        self.metadata = {
            'start_time': datetime.now().isoformat(),
            'version': os.getenv("TRANSLATION_VERSION", "adhoc")
        }

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Automated Markdown Translation Pipeline')
        parser.add_argument("--source-dir", default="trees", help="Source directory with Chinese markdown")
        parser.add_argument("--target-dir", default="trees_en", help="Target directory for English translations")
        parser.add_argument("--pr-reviewers", default="", help="Comma-separated GitHub reviewers")
        parser.add_argument("--metadata", default="", help="Additional metadata for tracking")
        return parser.parse_args()

    def run(self):
        try:
            # Phase 1: Detect Changes
            changed_files = self.detect_changes()
            if not changed_files:
                logger.info("No changes detected")
                return
            
            # Phase 2: Execute Translation
            translation_stats = self.execute_translation(changed_files)
            
            # Phase 3: Create Review Point
            self.create_review_point(translation_stats)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise

    def detect_changes(self) -> List[str]:
        """Identify modified/added markdown files"""
        changed = []
        for diff in self.repo.index.diff(None):
            if diff.change_type in ('A', 'M') and diff.a_path.endswith('.md'):
                abs_path = Path(diff.a_path).absolute()
                try:
                    if str(abs_path.relative_to(self.args.source_dir)).startswith('..'):
                        continue
                    changed.append(str(abs_path))
                except ValueError:
                    continue
        return changed

    def execute_translation(self, files: List[str]) -> Dict[str, int]:
        """Run batch translation with progress tracking"""
        rel_files = [str(Path(f).relative_to(self.args.source_dir)) for f in files]
        
        logger.info(f"Starting translation of {len(files)} files")
        stats = self.translator.batch_translate(
            input_dir=self.args.source_dir,
            output_dir=self.args.target_dir,
            specific_files=rel_files
        )
        
        if stats['success'] == 0:
            raise Exception("Translation failed for all files")
        
        return stats

    def create_review_point(self, stats: Dict[str, int]):
        """Commit changes and create PR"""
        # Configure Git
        self.repo.git.config("user.name", "Translation Pipeline")
        self.repo.git.config("user.email", "translation@community-blog")
        
        # Commit changes
        self.repo.git.add(A=True)
        commit_msg = f"""feat(translation): batch update {self.metadata['version']}

        Files processed:
        - Success: {stats['success']}
        - Failed: {stats['failed']}
        """
        self.repo.index.commit(commit_msg)
        
        # Push to dedicated branch
        branch_name = f"translation-{self.metadata['version']}"
        self.repo.git.push("origin", f"HEAD:{branch_name}", force=True)
        
        # Create PR
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        
        pr = repo.create_pull(
            title=f"[Bot] Translation Updates ({self.metadata['version']})",
            body=self.generate_pr_body(stats),
            head=branch_name,
            base="main",
            labels=["translation", "needs-review"]
        )
        
        # Manage reviewers
        if self.args.pr_reviewers:
            pr.create_review_request(
                reviewers=[r.strip() for r in self.args.pr_reviewers.split(",")]
            )

    def generate_pr_body(self, stats: Dict[str, int]) -> str:
        """Generate comprehensive PR description"""
        return f"""
## Translation Pipeline Report

**Batch ID**: {self.metadata['version']}  
**Start Time**: {self.metadata['start_time']}  
**Processed Files**: {stats['success']} succeeded, {stats['failed']} failed

### Quality Assurance Checklist:
1. [ ] Markdown structure validation
2. [ ] Technical term verification
3. [ ] Code block integrity check
4. [ ] URL functionality testing

### Approval Workflow:
- Reviewer 1: [ ] Approved
- Reviewer 2: [ ] Approved

> Automatically generated by translation pipeline
"""

if __name__ == "__main__":
    try:
        TranslationManager().run()
    except Exception as e:
        logger.error(f"Fatal pipeline error: {str(e)}")
        exit(1)