import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranslationError(Exception):
    """Custom exception for translation failures"""
    pass

class MarkdownTranslator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

    def translate_text(self, text: str) -> str:
        """Translate text while preserving technical content"""
        payload = {
            "model": "Pro/deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional technical translator. "
                        "Translate Chinese to English while EXACTLY preserving:"
                        "\n1. All Markdown formatting (headings, lists, etc)"
                        "\n2. Code blocks and inline code"
                        "\n3. URLs and YAML front matter"
                        "\n4. Technical terms (use glossary if available)"
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise TranslationError("Translation service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise TranslationError("Failed to process translation")

    def translate_file(self, input_path: str, output_path: str) -> bool:
        """Process single file with enhanced error handling"""
        try:
            # Read with explicit encoding and line handling
            with open(input_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()

            # Skip empty files
            if not content.strip():
                logger.warning(f"Skipped empty file: {input_path}")
                return False

            # Create output directory structure
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write with atomic write pattern
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8', newline='') as f:
                f.write(self.translate_text(content))
            
            # Atomic rename on success
            temp_path.replace(output_path)
            return True

        except TranslationError:
            return False
        except Exception as e:
            logger.error(f"Failed to process {input_path}: {str(e)}")
            return False

    def batch_translate(self, 
                      input_dir: str, 
                      output_dir: str, 
                      specific_files: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Batch translate with directory structure preservation
        
        Args:
            input_dir: Source directory path
            output_dir: Target directory path
            specific_files: Optional list of relative paths to process
            
        Returns:
            Dictionary with success/failure counts
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Resolve file list
        if specific_files:
            md_files = [input_path / f for f in specific_files]
        else:
            md_files = list(input_path.rglob('*.md'))
        
        stats = {'success': 0, 'failed': 0}
        for md_file in md_files:
            # Maintain relative path structure
            rel_path = md_file.relative_to(input_path)
            output_file = output_path / rel_path.with_name(f"{rel_path.stem}_en.md")
            
            if self.translate_file(str(md_file), str(output_file)):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Translation completed: {stats['success']} succeeded, {stats['failed']} failed")
        return stats

def load_config(config_path: str = None) -> Dict[str, str]:
    """Locate and load configuration from multiple possible locations"""
    search_paths = [
        Path("config.json"),
        Path(__file__).parent.parent / "config.json",
        Path.home() / ".config/community-blog.json"
    ]
    
    if config_path:
        search_paths.insert(0, Path(config_path))
    
    for path in search_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if config.get("api_key"):
                    return config
            except Exception as e:
                logger.warning(f"Config load failed for {path}: {str(e)}")
                continue
                
    raise FileNotFoundError("No valid config file found")