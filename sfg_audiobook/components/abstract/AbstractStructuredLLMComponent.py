import json
from abc import ABC
from time import sleep

import openai
from google import genai
from google.genai.errors import ServerError
from jinja2 import Template
import litellm
import os
from pydantic import BaseModel

from sfg_audiobook.sfg_types import PipelineData
from sfg_audiobook.structure.AbstractComponent import AbstractComponent


class AbstractStructuredLLMComponent(AbstractComponent, ABC):
    """
    Use LLMs with Jinja2 prompt templates to extract data from text.
    This component uses litellm to support many different LLM backends.
    """

    def __init__(self, params: dict[str, str], name: str = None, *args, **kwargs) -> None:
        super().__init__(params, name, *args, **kwargs)
        self._model = params.get("model", "openai/gpt-4o-mini")

        # Load prompt template from file
        if not params.get("system_prompt_template_file"):
            raise ValueError("system_prompt_template_file parameter is required and must be a valid file path.")
        with open(params["system_prompt_template_file"], "r") as f:
            self._system_prompt_template = Template(f.read())

        if not params.get("content_prompt_template_file"):
            raise ValueError("content_prompt_template_file parameter is required and must be a valid file path.")
        with open(params["content_prompt_template_file"], "r") as f:
            self._content_prompt_template = Template(f.read())

        # Check model supported params
        self._model_supported_params = litellm.get_supported_openai_params(model=self._model)

        self._model_name = self._model.split("/")[1]

        # Set API key
        self._api_provider = self._model.split("/")[0].lower()
        env_api_key_name = f"{self._api_provider.upper()}_API_KEY"
        self._api_key = os.environ.get(env_api_key_name)

        if not self._api_key:
            if self._api_provider.lower() == "ollama":  # Ollama does not require api key
                pass
            else:
                raise ValueError(
                    f"API key for {self._api_provider} is required. Set it in the params or as an environment variable {env_api_key_name}.")

    @staticmethod
    def get_attributes_help_text() -> str:
        return """\tAttribute (optional): model (str): litellm id of model to use. Default is "openai/gpt-4o-mini".
\tAttribute: system_prompt_template_file (str): Path to Jinja2 template file for the system prompt, meant for instructions (Whole PipelineData available in the template file).
\tAttribute: content_prompt_template_file (str): Path to Jinja2 template file for the prompt, meant for data.original_text (Whole PipelineData available in the template file).
\tEnvironment variable: {PROVIDER}_API_KEY (str): API key for chosen LLM model provider.
"""

    def setup(self, data: PipelineData):
        pass

    def predict(self, data: PipelineData, text: str, TargetModel: type(BaseModel), context_window_size: int = None):
        # Render the template with the text
        system_prompt = self._system_prompt_template.render({"data": data, "text": text})
        content_prompt = self._content_prompt_template.render({"data": data, "text": text})

        # Call LLM API
        while True:
            try:
                if self._api_provider == "ollama":
                    res = litellm.completion(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": content_prompt}
                        ],
                        format=TargetModel.model_json_schema(),
                        num_ctx=context_window_size if context_window_size else 16384,  # Set larger context window for the Ollama server to use with the model
                    )
                    response_json = res.choices[0].model_extra["message"].content

                elif self._api_provider == "gemini":
                    # litellm does not correctly support gemini JSON schemas validation, call gemini directly
                    # https://ai.google.dev/gemini-api/docs/structured-output?lang=python
                    client = genai.Client(api_key=self._api_key)
                    res = client.models.generate_content(
                        model=self._model_name,
                        contents=content_prompt,
                        config={
                            'response_mime_type': 'application/json',
                            'response_schema': TargetModel,
                            'system_instruction': system_prompt,
                        },
                    )
                    res_obj = res.parsed
                    response_json = res.text
                    if not res_obj:
                        raise ValueError(f"Gemini response can not be parsed correctly, finish reason: {res.candidates[0].finish_reason}, finish_message: {res.candidates[0].finish_message}, response text: '{response_json}', input content prompt: '{content_prompt}'.")
                    parsed_response = TargetModel.model_validate_json(response_json)
                    usage = res.usage_metadata
                    stats = {"prompt_tokens": usage.prompt_token_count, "completion_tokens": usage.candidates_token_count}
                    return parsed_response, stats

                else:
                    res = litellm.completion(
                        model=self._model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": content_prompt}
                        ],
                        response_format=TargetModel,  # litellm sucks with gemini and this does not make output json necessary valid, hell
                        # response_format={"type": "json_object"},
                        seed=42,  # Try to make the model as deterministic as possible between calls (even tho it is not possible: https://platform.openai.com/docs/advanced-usage/reproducible-outputs)
                        allowed_openai_params=['seed'],
                    )
                    response_json = res.choices[0].model_extra["message"].content
                break

            except (litellm.InternalServerError, openai.RateLimitError, ServerError) as e:
                print(f"LLM API internal server error: {e}")
                sleep(30)  # Sleep and try again

            except ValueError as e:
                print(f"LLM API value error: {e}")
                return None, None


            # except openai.RateLimitError as e:
            #     print(f"LLM API rate limit hit: {e}")
            #     sleep(30)  # Sleep and try again

        # Process the response
        try:
            # Models like to add ``` around the response sometimes, this will remove it if necessary
            first_opening_bracket = response_json.find("{")
            last_opening_bracket = response_json.rfind("}")
            response_json = response_json[first_opening_bracket:last_opening_bracket + 1]

            parsed_response = TargetModel.model_validate_json(response_json)

            usage = res.model_extra["usage"]
            stats = {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
            return parsed_response, stats

        except Exception as e:
            print(f"Error parsing LLM data: {e}")
            print(f"LLM response: {json.dumps(res, indent=2)}")
            print(f"LLM response_json: {response_json}")
            return None, None


# DO NOT REGISTER THIS ABSTRACT CLASS!
