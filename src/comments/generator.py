"""
Enhanced comment generator for LinkedIn posts with multilingual support
"""
import os
import subprocess
import time
import json
import re
from utils.logger import setup_logger
from config.settings import AI_MODEL, AI_TIMEOUT
from src.language_prompts import (
    get_comment_prompt, 
    detect_language,
)

logger = setup_logger(__name__)

class CommentGenerator:
    """Generate comments for LinkedIn posts with language detection"""
    
    def __init__(self, model=AI_MODEL):
        """
        Initialize the comment generator
        
        Args:
            model (str, optional): AI model to use. Defaults to AI_MODEL from settings.
        """
        self.model = model
        self.timeout = AI_TIMEOUT
    
    def generate(self, post_content, author_name=None, topic="recruiting", force_language=None):
        """
        Generate a comment for a LinkedIn post with language detection
        
        Args:
            post_content (str): Content of the post
            author_name (str, optional): Name of the post author. Defaults to None.
            topic (str, optional): Topic of the post. Defaults to "recruiting".
            force_language (str, optional): Force a specific language. Defaults to None.
            
        Returns:
            tuple: (comment, generation_info)
        """
        logger.info("Generating comment for post")
        
        try:
            # Detect language if not forced
            if not force_language:
                detected_language = detect_language(post_content)
                logger.info(f"Detected language: {detected_language}")
            else:
                detected_language = force_language
                logger.info(f"Using forced language: {detected_language}")
            
            # If language is unknown, default to English
            if detected_language == "unknown":
                detected_language = "en"
                logger.info("Unknown language detected, defaulting to English")
            
            # Truncate post content if too long
            post_preview = post_content
            if len(post_content) > 1500:
                post_preview = post_content[:1500] + "..."
            
            # Create the prompt
            prompt = get_comment_prompt(
                language=detected_language,
                topic=topic,
                post_content=post_preview,
                author_name=author_name or "LinkedIn User"
            )
            
            # Generate comment with fallback mechanism
            comment = self._generate_with_ollama(prompt)
            
            # Check if comment is empty or too short
            if not comment or len(comment.strip()) < 10:
                logger.warning("First attempt produced empty or too short comment, trying again")
                
                # Try one more time
                comment = self._generate_with_ollama(prompt)
                
                # If still empty, use fallback
                if not comment or len(comment.strip()) < 10:
                    logger.warning("Second attempt also failed, using fallback")
                    comment = self._fallback_comment(author_name, detected_language)
                    return comment, "FALLBACK_EMPTY"
            
            # Clean up the comment
            comment = self._clean_comment(comment, detected_language)
            
    

            # Log success and return the comment
            logger.info(f"Successfully generated comment in {detected_language}")
            return comment, f"AI_GENERATED"
            
        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            # Return a fallback comment
            return self._fallback_comment(author_name, force_language or "en"), "ERROR_EXCEPTION"
        
    def _clean_comment(self, comment, language):
        """
        Clean up the comment to ensure it's properly formatted
        
        Args:
            comment (str): Raw generated comment
            language (str): Language code
            
        Returns:
            str: Cleaned comment
        """
        from config.settings import FRIBL_LINK
        
        # Remove any quotes that might surround the comment
        comment = comment.strip('"\'')
        
        # Check if there's a step-by-step reasoning and extract only the final answer
        step_indicators = [
            "Final Response:", "Réponse finale:", "Respuesta final:",
            "5.", "Step 5:", "Paso 5:", "Étape 5:"
        ]
        
        for indicator in step_indicators:
            if indicator in comment:
                # Extract everything after the final step indicator
                parts = comment.split(indicator)
                if len(parts) > 1:
                    comment = parts[1].strip()
                    break
        
        # Remove any "Answer:" or similar prefixes
        prefixes_to_remove = [
            "Answer:", "Réponse:", "Respuesta:", 
            "Comment:", "Commentaire:", "Comentario:",
            "Here's the comment:", "Voici le commentaire:", "Aquí está el comentario:"
        ]
        
        for prefix in prefixes_to_remove:
            if comment.startswith(prefix):
                comment = comment[len(prefix):].strip()
        
        # Make sure there are no trailing instructions
        if "INSTRUCTIONS:" in comment:
            comment = comment.split("INSTRUCTIONS:")[0].strip()
        
        # Make sure there are no markdown-style bullet points
        comment = comment.replace("* ", "").replace("- ", "")
        
        # Make sure there are no extra new lines
        comment = " ".join(line.strip() for line in comment.strip().split("\n") if line.strip())
        
        # Remove any Fribl links to prevent duplication
        # Remove the exact link
        comment = comment.replace(FRIBL_LINK, "")
        
        # Remove any markdown links containing the Fribl URL
        import re
        comment = re.sub(r'\[.*?\]\(.*?fribl\.co.*?\)', '', comment, flags=re.IGNORECASE)
        
        # Remove Markdown links with empty parentheses like [Fribl]()
        comment = re.sub(r'\[Fribl\]\(\s*\)', '', comment, flags=re.IGNORECASE)
        
        # Remove more general Markdown links containing Fribl word in brackets
        comment = re.sub(r'\[[^\]]*?[Ff]ribl[^\]]*?\]\(\s*[^)]*?\)', '', comment, flags=re.IGNORECASE)
        
        # Remove any plain text URLs containing fribl.co
        comment = re.sub(r'https?://(?:www\.)?(?:app\.)?fribl\.co/\S*', '', comment, flags=re.IGNORECASE)
        
        # Clean up any excess whitespace that might have been created
        comment = re.sub(r'\s+', ' ', comment).strip()
        
        return comment.strip()


    

    def _generate_with_ollama(self, prompt):
        """
        Generate text using Ollama with fallback to API
        
        Args:
            prompt (str): Prompt for the model
            
        Returns:
            str: Generated text
        """
        # First try with subprocess
        response = self._generate_with_subprocess(prompt)
        
        # If subprocess failed, try with API
        if not response or len(response.strip()) < 10:
            logger.warning("Subprocess generation failed or returned too short response, trying API fallback")
            response = self._generate_with_api(prompt)
        
        return response

    def _generate_with_subprocess(self, prompt):
        """
        Generate text using Ollama via subprocess
        
        Args:
            prompt (str): Prompt for the model
            
        Returns:
            str: Generated text
        """
        try:
            logger.debug(f"Using subprocess with model: {self.model}")
            
            # Encode the prompt to avoid character issues
            prompt_encoded = prompt.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            
            # Configure Ollama command
            cmd = ["ollama", "run", self.model, "--nowordwrap", prompt_encoded]
            
            # Execute process with timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Set a timer
            start_time = time.time()
            response = ""
            
            while process.poll() is None:
                # Check if timeout is exceeded
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Ollama subprocess timed out after {self.timeout} seconds")
                    process.terminate()
                    break
                
                # Read process output
                if process.stdout:
                    line = process.stdout.readline()
                    if line:
                        response += line
                
                # Small delay to avoid high CPU usage
                time.sleep(0.1)
            
            # Get any remaining output
            if process.stdout:
                remaining_output = process.stdout.read()
                if remaining_output:
                    response += remaining_output
            
            # Clean the response
            response = self._clean_up_response(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating with Ollama subprocess: {e}")
            return ""

    def _generate_with_api(self, prompt):
        """
        Generate text using Ollama HTTP API
        
        Args:
            prompt (str): Prompt for the model
            
        Returns:
            str: Generated text
        """
        try:
            import requests
            
            logger.debug(f"Using Ollama API with model: {self.model}")
            
            # Ollama API endpoint
            url = "http://localhost:11434/api/generate"
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False  # Set to False for simpler response handling
            }
            
            # Send the request with timeout
            response = requests.post(url, json=payload, timeout=self.timeout)
            
            if response.status_code == 200:
                # Parse the response
                try:
                    data = response.json()
                    generated_text = data.get("response", "")
                    
                    # Clean the response
                    cleaned_response = self._clean_up_response(generated_text)
                    return cleaned_response
                except json.JSONDecodeError:
                    # If not a single JSON object, try parsing as streaming response
                    lines = response.text.strip().split("\n")
                    full_response = ""
                    
                    for line in lines:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                full_response += data["response"]
                        except json.JSONDecodeError:
                            continue
                    
                    # Clean the response
                    cleaned_response = self._clean_up_response(full_response)
                    return cleaned_response
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            logger.error(f"Error generating with Ollama API: {e}")
            return ""







    def _clean_up_response(self, response):
        """
        Clean up the response from Ollama
        
        Args:
            response (str): Raw response from Ollama
            
        Returns:
            str: Cleaned up response
        """
        try:
            # Split by lines and remove any warnings or model info
            lines = response.strip().split("\n")
            cleaned_lines = []
            
            for line in lines:
                # Skip lines that are likely to be model information or warnings
                if "ollama" in line.lower() or "model" in line.lower() or "warning" in line.lower():
                    continue
                cleaned_lines.append(line)
            
            # Join the cleaned lines
            cleaned_response = "\n".join(cleaned_lines).strip()
            
            # Remove any markdown formatting
            if cleaned_response.startswith("```") and cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[3:-3].strip()
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Error cleaning up response: {e}")
            return response
    
    def _fallback_comment(self, author_name=None, language="en"):
        """
        Generate a fallback comment if something goes wrong
        
        Args:
            author_name (str, optional): Name of the post author. Defaults to None.
            language (str, optional): Language to use. Defaults to "en".
            
        Returns:
            str: Fallback comment
        """
        # Get first name if available
        first_name = ""
        if author_name:
            first_name = author_name.split()[0]
        
        # Select fallback comment based on language
        if language == "fr":
            if first_name:
                return f"Ce processus semble complexe. Fribl pourrait vous aider à le simplifier!"
            else:
                return f"Intéressant! Fribl pourrait vraiment optimiser ce processus de recrutement."
        elif language == "es":
            if first_name:
                return f"Este proceso podría optimizarse. ¡Fribl tiene la solución perfecta!"
            else:
                return f"¡Interesante! Fribl podría agilizar este proceso de reclutamiento."
        else:  # Default to English
            if first_name:
                return f"This looks like a complex process. Fribl could help streamline it!"
            else:
                return f"Interesting! Fribl could really optimize this recruitment process."