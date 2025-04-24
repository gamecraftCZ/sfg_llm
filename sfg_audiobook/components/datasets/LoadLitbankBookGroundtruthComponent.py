import os
from dataclasses import dataclass
from pathlib import Path

from common.errors import ComponentParserError
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart
from structure.AbstractComponent import AbstractComponent


@dataclass
class LitBankQuote:
    quote_text: str
    quote_id: str
    quote_attribution: str  # Character name who said the quote, eg. FAIR_BOY_OFFICER-18

@dataclass
class LitBankBook:
    raw_text: str  # Raw text of the book
    text_parts: list[TextPart]  # Text split on other/quote changing. character_identifier one of the characters
    characters: list[str]  # character names, eg. FAIR_BOY_OFFICER-18
    quotes: list[LitBankQuote]  # List of quotes in the book, with their attribution


class LoadLitbankBookGroundtruthComponent(AbstractComponent):
    """
    Components that loads groundtruth quotes attribution labels from LitBank dataset.
    """

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "repo" not in params:
            raise ComponentParserError(f"repo parameter is required for {self.__class__.__name__}.")
        if "book_id" not in params:
            raise ComponentParserError(f"book_id parameter is required for {self.__class__.__name__}.")

    @staticmethod
    def get_help() -> str:
        return """Loads groundtruth from litbank dataset into additional_attributes["characters_gt"] and additional_attributes["text_as_parts_gt"].
\tAttribute: repo (str): Path to the Litbank repository.
\tAttribute: book_id (str): Book ID to load.
\tAttribute (optional): use_gt_text (bool): If True, use the groundtruth text as original text. Default is False.
\tAttribute (optional): use_gt_characters (bool): If True, use the groundtruth characters as predicted characters. Default is False.
\tAttribute (optional): use_gt_text_as_parts (bool): If True, use the groundtruth text_as_parts as predicted text_as_parts. Default is False."""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        litbank_repo_path = Path(self._params["repo"])
        book_id = self._params["book_id"]
        book = LoadLitbankBookGroundtruthComponent.load_litbank_book(book_id, litbank_repo_path)

        data.additional_attributes["original_text_gt"] = book.raw_text
        data.additional_attributes["characters_gt"] = book.characters
        data.additional_attributes["text_as_parts_gt"] = book.text_parts

        if self._params["use_gt_text"] and self._params["use_gt_text"].lower() == "true":
            data.original_text = book.raw_text

    @staticmethod
    def list_litbank_books(litbank_repo_path: Path) -> list[str]:
        """
        List all the books in the Litbank repository.

        Args:
            litbank_repo_path (Path): Path to the Litbank repository.

        Returns:
            list[str]: List of book IDs.
        """
        # List all files in the Litbank repository that matches *.ann
        return [f.split(".")[0] for f in os.listdir(litbank_repo_path / "original") if f.endswith(".ann")]

    @staticmethod
    def _load_from_file(filename: Path) -> str:
        with open(filename, "r") as f:
            return f.read()

    @staticmethod
    def load_litbank_book(book_id: str, litbank_repo_path: Path) -> LitBankBook:
        """
        Parse LitBank text and annotation files into a LitBankBook object.

        Returns:
            A LitBankBook object containing the parsed data
        """
        # full_book_text = load_from_file(litbank_repo_path / "original" / f"{book_id}.txt")
        book_text = LoadLitbankBookGroundtruthComponent._load_from_file(litbank_repo_path / "quotations" / "tsv" / f"{book_id}_brat.txt")
        annotation_text = LoadLitbankBookGroundtruthComponent._load_from_file(litbank_repo_path / "quotations" / "tsv" / f"{book_id}_brat.ann")

        # Parse the quotes and attributions from the annotation file
        quotes_dict, attribution_dict = LoadLitbankBookGroundtruthComponent._parse_annotations(annotation_text)

        # Combine quotes and attributions
        quotes = []
        characters = set()
        for quote_id, quote_data in quotes_dict.items():
            attribution = attribution_dict.get(quote_id)
            if attribution:
                characters.add(attribution)
                quotes.append(LitBankQuote(
                    quote_text=quote_data['text'],
                    quote_id=quote_id,
                    quote_attribution=attribution
                ))

        # Split the book text into sentences
        sentences = book_text.strip().split('\n')

        # Create a map of sentence ranges that are quotes
        quote_ranges = {}
        for quote_id, quote_data in quotes_dict.items():
            start_sent = quote_data['start_sent']
            end_sent = quote_data['end_sent']
            start_token = quote_data['start_token']
            end_token = quote_data['end_token']

            for sent_idx in range(start_sent, end_sent + 1):
                if sent_idx not in quote_ranges:
                    quote_ranges[sent_idx] = []
                quote_ranges[sent_idx].append({
                    'quote_id': quote_id,
                    'start_token': start_token if sent_idx == start_sent else 0,
                    'end_token': end_token if sent_idx == end_sent else len(sentences[sent_idx].split()),
                    'attribution': attribution_dict.get(quote_id)
                })

        # Generate TextParts by walking through the sentences and identifying quotes
        text_parts = []
        current_text = ""
        current_type = "other"
        current_character = None

        for sent_idx, sentence in enumerate(sentences):
            tokens = sentence.split()

            if sent_idx in quote_ranges:
                # Sort quotes by their start token
                sent_quotes = sorted(quote_ranges[sent_idx], key=lambda q: q['start_token'])

                current_pos = 0
                for quote_info in sent_quotes:
                    # Add text before the quote
                    if current_pos < quote_info['start_token']:
                        before_text = " ".join(tokens[current_pos:quote_info['start_token']])
                        if current_type == "quote" or (current_type == "other" and before_text.strip()):
                            # Finish current part
                            if current_text:
                                text_parts.append(TextPart(
                                    text=current_text.strip(),
                                    type=current_type,
                                    character_identifier=current_character
                                ))
                            # Start new "other" part
                            current_text = before_text
                            current_type = "other"
                            current_character = None
                        else:
                            # Continue current "other" part
                            current_text += " " + before_text if current_text else before_text

                    # Add the quote
                    quote_text = " ".join(tokens[quote_info['start_token']:quote_info['end_token'] + 1])
                    if current_type == "quote" and current_character == quote_info['attribution']:
                        # Continue current quote part for the same character
                        current_text += " " + quote_text if current_text else quote_text
                    else:
                        # Finish current part
                        if current_text:
                            text_parts.append(TextPart(
                                text=current_text.strip(),
                                type=current_type,
                                character_identifier=current_character
                            ))
                        # Start new quote part
                        current_text = quote_text
                        current_type = "quote"
                        current_character = quote_info['attribution']

                    current_pos = quote_info['end_token'] + 1

                # Add remaining text in the sentence
                if current_pos < len(tokens):
                    after_text = " ".join(tokens[current_pos:])
                    if current_type == "quote":
                        # Finish current quote part
                        if current_text:
                            text_parts.append(TextPart(
                                text=current_text.strip(),
                                type=current_type,
                                character_identifier=current_character
                            ))
                        # Start new "other" part
                        current_text = after_text
                        current_type = "other"
                        current_character = None
                    else:
                        # Continue current "other" part
                        current_text += " " + after_text if current_text else after_text
            else:
                # No quotes in this sentence
                if current_type == "quote":
                    # Finish current quote part
                    if current_text:
                        text_parts.append(TextPart(
                            text=current_text.strip(),
                            type=current_type,
                            character_identifier=current_character
                        ))
                    # Start new "other" part
                    current_text = sentence
                    current_type = "other"
                    current_character = None
                else:
                    # Continue current "other" part
                    current_text += " " + sentence if current_text else sentence

        # Add the last part if exists
        if current_text:
            text_parts.append(TextPart(
                text=current_text.strip(),
                type=current_type,
                character_identifier=current_character
            ))

        return LitBankBook(
            raw_text=book_text,  # TODO use full_book_text trimmed to book_text length as raw_text.
            text_parts=text_parts,
            characters=list(characters),
            quotes=quotes
        )

    @staticmethod
    def _parse_annotations(annotation_text: str) -> tuple[dict, dict]:
        """
        Parse the annotation file into quotes and attributions.

        Args:
            annotation_text: The content of the annotation file

        Returns:
            A tuple of (quotes_dict, attribution_dict)
        """
        quotes_dict = {}
        attribution_dict = {}

        for line in annotation_text.strip().split('\n'):
            if not line.strip():
                continue

            parts = line.split('\t')
            if parts[0] == 'QUOTE':
                quote_id = parts[1]
                start_sent = int(parts[2])
                start_token = int(parts[3])
                end_sent = int(parts[4])
                end_token = int(parts[5])
                quote_text = parts[6]

                quotes_dict[quote_id] = {
                    'text': quote_text,
                    'start_sent': start_sent,
                    'start_token': start_token,
                    'end_sent': end_sent,
                    'end_token': end_token
                }
            elif parts[0] == 'ATTRIB':
                quote_id = parts[1]
                speaker = parts[2]
                attribution_dict[quote_id] = speaker

        return quotes_dict, attribution_dict


ComponentsRegister.register_component("load_litbank_book_groundtruth", LoadLitbankBookGroundtruthComponent)
