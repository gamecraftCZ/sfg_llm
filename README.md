# SFG audiobook

Modular framework for character and direct speech extraction and converting it to spoken text.

This is a codebase for SFG 


The code is designed in a composable way using components and pipelines. When running the program, it first parses defined components into a list of component instances with their parameter sets and composes a pipeline from them. Running the pipeline, each of its components is run from the `Pipeline` object one by one passing and mutating a single PipelineData state object.

## Usage

Run `sfg_audibook` in terminal to invoke the CLi interface for SFG audiobook project.

List available components with their arguments: `sfg_audiobook --list_components`

Arguments for components are defined in [] brackets, separated by comma in format name=value. 
If you prepend ComponentName with '!' it will not be run (only setup will be executed).

Example of pipeline to predict book A Handful of Dust from PDNC dataset and evaluate the quotation results:
```bash
sfg_audibook
  --pipeline custom
  --component load_pdnc_book_groundtruth[repo=../project-dialogism-novel-corpus,book=AHandfulOfDust,use_gt_text=true,use_gt_characters=true,use_gt_text_as_parts=false]
  --component llm_quotation_attributor[system_prompt_template_file=templates/quotation_extraction_and_attribution_system_prompt_complex_fewshot.jinja,content_prompt_template_file=templates/quotation_extraction_and_attribution_prompt_content_1.jinja,chunk_size=4000,chunk_overlap=256,ignore_errors=True,model=gemini/gemini-2.0-flash]
  --component evaluation_quotation_extraction[]
  --component save_pipeline_data_json[file=output/a_handful_of_dust_data.json]
```

Example of pipeline to convert a raw book text to spoken audio:
```bash
sfg_audibook
  --pipeline custom
  --component load_text_from_file[file=book_text.txt]
  --component llm_character_extractor[system_prompt_template_file=templates/character_extraction_system_prompt_complex.jinja,content_prompt_template_file=templates/character_extraction_prompt_content_1.jinja,model=gemini/gemini-2.0-flash]
  --component llm_quotation_attributor[system_prompt_template_file=templates/quotation_extraction_and_attribution_system_prompt_complex_fewshot.jinja,content_prompt_template_file=templates/quotation_extraction_and_attribution_prompt_content_1.jinja,chunk_size=4000,chunk_overlap=256,ignore_errors=True,model=gemini/gemini-2.0-flash]
  --component llm_character_to_speaker_matcher[system_prompt_template_file=templates/character_matcher_system_prompt_complex.jinja,content_prompt_template_file=templates/character_matcher_prompt_content_1.jinja,model=gemini/gemini-2.0-flash]
  --component azure_tts[lang=en,out_file=book_voice_output.mp3]
```


## Components

**LoadTextFromFileComponent**: Loads book text into pipeline data for further processing.

**LLMCharacterExtractorComponent**: Given a full book text, uses LLM to extract list of characters with a short description of them.
Uses \texttt{litellm} python package to be able to call multiple LLM APIs without need of code modifications. Prompts given to it are formatted using Jinja2 library.

**LLMQuotationAttributorComponent**: Given a full book text and a list of story characters, uses LLM to split the text into quotes and other text. Before prediction, it splits the input text into chunks of configurable number of string characters with configurable number of overlapping characters between chunks. This allows for processing longer books in parallel and reduces the required context length.
It also uses the \texttt{litellm} Python package to be able to call multiple LLM APIs without code modifications. Prompts are formatted using the Jinja2 library. We use structured output functionality to constrain the models to output only a valid json data that matches the provided schema.

**LLMCharacterToSpeakerMatcherComponent**: Given a characters list and a list of speakers available in the TTS system, assigns a speaker to each of the characters.
Uses \texttt{litellm} python package to be able to call multiple LLM API provides without code modifications. Prompts given to it are formted using Jinja2 library.

**AzureTTSComponent**: Given a book text parts (quotes and other text) with assigned characters and a list of characters with assigned speakers, converts the text to speech. It first converts the text into Speech Synthesis Markup Language which is then fed into Azure Text to speech engine.

**SavePipelineDataToJsonComponent**: saves currently processed data to json

**LoadPipelineDataFromJsonComponent**: loads currently processed data from json

**LoadLitbankBookGroundtruthComponent**: loads Litbank dataset to the pipeline as groundtruth data

**LoadPDNCGroundtruthComponent**: loads PDNC dataset to the pipeline as groundtruth data

**QuotationExtractionAndAttributionEvaluationComponent**: evaluates extracted quotes and their attribution with the groundtruth data 

## Acknowledgment

This project was financially supported by the Student Faculty Grants programme provided by the Faculty of Mathematics and Physics, Charles University.
