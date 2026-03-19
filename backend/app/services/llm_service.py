import os
from loguru import logger
from app.core.config import settings


class LLMService:
    """
    LLM Service supporting both local (Ollama) and cloud (Groq) providers.
    Switch between providers using LLM_PROVIDER env variable.
    """

    # Local Ollama models
    LOCAL_MODELS = {
        "test_case": "llama3",
        "general_chat": "gemma2"
    }

    # Groq cloud models (much faster!)
    CLOUD_MODELS = {
        "test_case": settings.GROQ_MODEL_TEST_CASE,
        "general_chat": settings.GROQ_MODEL_GENERAL_CHAT
    }

    MODEL_OPTIONS = {
        "test_case": {
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "general_chat": {
            "max_tokens": 2048,
            "temperature": 0.7,
        }
    }

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        logger.info(f"Initializing LLM Service with provider: {self.provider}")

        if self.provider == "cloud":
            self._init_groq()
        else:
            self._init_ollama()

    def _init_groq(self):
        """Initialize Groq client for cloud inference"""
        try:
            from groq import Groq
            api_key = settings.GROQ_API_KEY
            if not api_key:
                raise ValueError("GROQ_API_KEY not set in environment")
            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized successfully")
            logger.info(f"Available cloud models: {self.CLOUD_MODELS}")
        except ImportError:
            logger.error("groq package not installed. Run: pip install groq")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            raise

    def _init_ollama(self):
        """Initialize Ollama for local inference"""
        try:
            import ollama
            self.ollama = ollama
            logger.info("Ollama client initialized successfully")
            logger.info(f"Available local models: {self.LOCAL_MODELS}")
        except ImportError:
            logger.error("ollama package not installed. Run: pip install ollama")
            raise

    def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: str = "general_chat"
    ) -> str:
        """Generate response using configured provider"""
        if self.provider == "cloud":
            return self._generate_groq(system_prompt, user_prompt, mode)
        else:
            return self._generate_ollama(system_prompt, user_prompt, mode)

    def _generate_groq(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: str
    ) -> str:
        """Generate response using Groq cloud API"""
        model = self.CLOUD_MODELS.get(mode, self.CLOUD_MODELS["general_chat"])
        options = self.MODEL_OPTIONS.get(mode, self.MODEL_OPTIONS["general_chat"])

        try:
            logger.info(f"Sending request to Groq using model: {model}")

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=options["max_tokens"],
                temperature=options["temperature"]
            )

            result = response.choices[0].message.content
            logger.info(f"Received response from Groq ({model})")
            return result

        except Exception as e:
            logger.exception(f"Groq API Error with model {model}")
            raise e

    def _generate_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        mode: str
    ) -> str:
        """Generate response using local Ollama"""
        model = self.LOCAL_MODELS.get(mode, self.LOCAL_MODELS["general_chat"])
        options = self.MODEL_OPTIONS.get(mode, self.MODEL_OPTIONS["general_chat"])

        # Convert to Ollama format
        ollama_options = {
            "num_predict": options["max_tokens"],
            "temperature": options["temperature"]
        }

        try:
            logger.info(f"Sending request to Ollama using model: {model}")

            response = self.ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options=ollama_options
            )

            logger.info(f"Received response from Ollama ({model})")
            return response["message"]["content"]

        except Exception as e:
            logger.exception(f"Ollama Error with model {model}")
            raise e


llm_service = LLMService()
