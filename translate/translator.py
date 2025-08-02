import os
import requests
from pathlib import Path
from typing import Dict, List, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

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
        self.glossary = self.load_glossary()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def translate_text(self, text: str) -> str:
        """Translate with technical content preservation"""
        payload = {
            "model": "Pro/deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a senior technical translator. Follow these rules:\n"
                        "1. EXACTLY preserve Markdown structure\n"
                        "2. NEVER modify code blocks\n"
                        "3. Keep URLs and YAML front matter unchanged\n"
                        f"4. Use this glossary:\n{self.format_glossary()}\n"
                        "5. Maintain consistent technical terminology"
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
            logger.error(f"API request failed (attempt {self.translate_text.retry.statistics['attempt_number']}): {str(e)}")
            raise TranslationError("Translation service error")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise TranslationError("Processing failure")

    def load_glossary(self) -> Dict[str, str]:
        """Load technical term glossary"""
        glossary_path = Path("translate/glossary.json")
        if glossary_path.exists():
            try:
                with open(glossary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Glossary load failed: {str(e)}")
        return {}

    def format_glossary(self) -> str:
        """Format glossary for API prompt"""
        return "\n".join(f"{k} => {v}" for k, v in self.glossary.items())

    def translate_file(self, input_path: str, output_path: str) -> bool:
        """Process single file with atomic writes"""
        try:
            with open(input_path, 'r', encoding='utf-8', newline='') as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"Skipped empty file: {input_path}")
                return False

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write pattern
            temp_path = output_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8', newline='') as f:
                f.write(self.translate_text(content))
            
            temp_path.replace(output_path)
            return True

        except TranslationError:
            return False
        except Exception as e:
            logger.error(f"File processing error ({input_path}): {str(e)}")
            return False

    def batch_translate(self, 
                      input_dir: str, 
                      output_dir: str, 
                      specific_files: Optional[List[str]] = None) -> Dict[str, int]:
        """Execute batch translation with structure preservation"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        files = [input_path / f for f in specific_files] if specific_files else list(input_path.rglob('*.md'))
        
        stats = {'success': 0, 'failed': 0}
        for md_file in files:
            rel_path = md_file.relative_to(input_path)
            output_file = output_path / rel_path.with_name(f"{rel_path.stem}_en.md")
            
            if self.translate_file(str(md_file), str(output_file)):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        logger.info(f"Batch completed - Success: {stats['success']}, Failed: {stats['failed']}")
        return stats