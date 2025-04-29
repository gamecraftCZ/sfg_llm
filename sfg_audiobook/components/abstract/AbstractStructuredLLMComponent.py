import json
from abc import ABC
from time import sleep

from jinja2 import Template
import litellm
import os
from pydantic import BaseModel

from sfg_types import PipelineData
from structure.AbstractComponent import AbstractComponent


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

        # Set API key
        api_provider = self._model.split("/")[0]
        env_api_key_name = f"{api_provider.upper()}_API_KEY"
        self._api_key = params.get("api_key") or os.environ.get(env_api_key_name)
        if params.get("api_key"):
            os.environ[env_api_key_name] = self._api_key

        if not self._api_key:
            raise ValueError(
                f"API key for {api_provider} is required. Set it in the params or as an environment variable {env_api_key_name}.")

    @staticmethod
    def get_attributes_help_text() -> str:
        return """\tAttribute (optional): model (str): litellm id of model to use. Default is "openai/gpt-4o-mini".
\tAttribute (optional): api_key (str): API key for chosen . Default is `api_key=os.environ.get("OPENAI_API_KEY")`.
\tAttribute: system_prompt_template_file (str): Path to Jinja2 template file for the system prompt, meant for instructions (Whole PipelineData available in the template file).
\tAttribute: content_prompt_template_file (str): Path to Jinja2 template file for the prompt, meant for data.original_text (Whole PipelineData available in the template file).
"""

    def setup(self, data: PipelineData):
        pass

    def predict(self, data: PipelineData, text: str, TargetModel: type(BaseModel)):
        # Render the template with the text
        system_prompt = self._system_prompt_template.render({"data": data, "text": text})
        content_prompt = self._content_prompt_template.render({"data": data, "text": text})

        # Call LLM API
        # Try 5 times in case something bad happens
        for i in range(5):
            try:
                res = litellm.completion(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content_prompt}
                    ],
                    response_format=TargetModel,  # litellm sucks with gemini and this does not make output json necessary valid
                    # response_format={"type": "json_object"},
                    seed=42,  # Try to make the model as deterministic as possible between calls (even tho it is not possible: https://platform.openai.com/docs/advanced-usage/reproducible-outputs)
                )
            except Exception as e:
                print(f"Error calling LLM API: {e}")
                if i == 4:
                    raise e
                sleep(60)  # Sleep one second

        # Process the response
        try:
            response_json = res.choices[0].model_extra["message"].content

            # Models like to add ``` around the response sometimes, this will remove it.
            first_opening_bracket = response_json.find("{")
            last_opening_bracket = response_json.rfind("}")
            response_json = response_json[first_opening_bracket:last_opening_bracket + 1]

            parsed_response = TargetModel.model_validate_json(response_json)

            usage = res.model_extra["usage"]
            stats = {"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
            return parsed_response, stats

        except json.JSONDecodeError as e:
            print(f"Error parsing character data: {e}")
            print(f"Response: {res}")
            return None, None


# DO NOT REGISTER THIS ABSTRACT CLASS!
