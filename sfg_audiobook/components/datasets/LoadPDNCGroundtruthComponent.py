import os
from pathlib import Path
import csv
import json
from common.errors import ComponentParserError
from components.ComponentsRegister import ComponentsRegister
from sfg_types import PipelineData, TextPart, Character, TextPartType, CharacterType, CharacterGender
from structure.AbstractComponent import AbstractComponent


class LoadPDNCGroundtruthComponent(AbstractComponent):
    """
    Components that loads groundtruth quotes attribution labels from Project Dialogism Novel Corpus dataset.
    """

    def __init__(self, params: dict[str, str], *args, **kwargs) -> None:
        super().__init__(params, *args, **kwargs)
        if "repo" not in params:
            raise ComponentParserError(f"repo parameter is required for {self.__class__.__name__}.")
        if "book_id" not in params:
            raise ComponentParserError(f"book_id parameter is required for {self.__class__.__name__}.")

    @staticmethod
    def get_help() -> str:
        return """Loads groundtruth from Project Dialogism Novel Corpus dataset into additional_attributes["characters_gt"], additional_attributes["text_as_parts_gt"] and additional_attributes["original_text_gt"].
\tAttribute: repo (str): Path to the cloned PDNC repository (github.com/Priya22/project-dialogism-novel-corpus).
\tAttribute: book_id (str): Book ID to load.
\tAttribute (optional): use_gt_text (bool): If True, use the groundtruth text as original text. Default is False.
\tAttribute (optional): use_gt_characters (bool): If True, use the groundtruth characters as predicted characters. Default is False.
\tAttribute (optional): use_gt_text_as_parts (bool): If True, use the groundtruth text_as_parts as predicted text_as_parts. Default is False."""

    def setup(self, data: PipelineData):
        pass

    def run(self, data: PipelineData):
        repo_path = Path(self._params["repo"])
        book_id = self._params["book_id"]

        characters, alias_character_mapping = LoadPDNCGroundtruthComponent.load_pdnc_characters(book_id, repo_path)
        data.additional_attributes["characters_gt"] = characters

        text_parts = LoadPDNCGroundtruthComponent.load_pdnc_text_parts(book_id, repo_path, alias_character_mapping)
        data.additional_attributes["text_as_parts_gt"] = text_parts
        data.additional_attributes["original_text_gt"] = "".join([part.text for part in text_parts])

        if self._params.get("use_gt_text") and self._params["use_gt_text"].lower() == "true":
            data.original_text = data.additional_attributes["original_text_gt"]

        if self._params.get("use_gt_characters") and self._params["use_gt_characters"].lower() == "true":
            data.characters = data.additional_attributes["characters_gt"]

        if self._params.get("use_gt_text_as_parts") and self._params["use_gt_text_as_parts"].lower() == "true":
            data.text_as_parts = data.additional_attributes["text_as_parts_gt"]

    @staticmethod
    def list_pdnc_books(pdnc_repo_path: Path) -> list[str]:
        """
        List all the books in the PDNC repository.

        Args:
            pdnc_repo_path (Path): Path to the PDNC repository.

        Returns:
            list[str]: List of book IDs.
        """
        # One folder per book
        return list(os.listdir(pdnc_repo_path / "data"))

    @staticmethod
    def _load_from_file(filename: Path) -> str:
        with open(filename, "r") as f:
            return f.read()

    @staticmethod
    def _character_identifier_from_name_and_id(name: str, id: str) -> str:
        """
        Generate a unique identifier for a character based on its name and ID.

        Args:
            name (str): The name of the character.
            id (str): The ID of the character.

        Returns:
            str: The unique identifier for the character.
        """
        return f"{name.upper().replace(' ', '_').replace('.', '')}_{id}"

    @staticmethod
    def _parse_aliases(aliases_str: str) -> list[str]:
        """
        Parse a string of aliases into a list.
        Why, because the format is all over the place. It can use both single ' and double " as quotes,
            and sometimes it is in ['Mama'] and sometimes in {'Joyce'}.

        Args:
            aliases_str (str): The string containing aliases.

        Returns:
            list[str]: List of aliases.
        """
        aliases = []

        a = aliases_str.strip()[1:-1]
        a_spl = a.split(',')
        for dirty_name in a_spl:
            # Remove quotes and spaces
            name = dirty_name.strip()[1:-1]
            aliases.append(name)

        return aliases

    @staticmethod
    def load_pdnc_characters(book_id: str, pdnc_repo_path: Path) -> tuple[list[Character], dict[str, Character]]:
        """
        Load characters from the PDNC dataset.

        Args:
            book_id (str): The book ID to load.
            pdnc_repo_path (Path): Path to the PDNC repository.

        Returns:
            list[Character]: List of characters in the book.\
            dict[str, Character]: Mapping of all character aliases to their character object
        """
        characters = []
        alias_character_mapping = {}
        with open(pdnc_repo_path / "data" / book_id / "character_info.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                aliases = LoadPDNCGroundtruthComponent._parse_aliases(row["Aliases"])
                character = Character(
                    name=row["Main Name"],
                    identifier=LoadPDNCGroundtruthComponent._character_identifier_from_name_and_id(row["Main Name"], row["Character ID"]),
                    type={"major": CharacterType.MAIN, "minor": CharacterType.MINOR, "intermediate": CharacterType.SUPPORT}[row["Category"]],
                    gender={"M": CharacterGender.MALE, "F": CharacterGender.FEMALE, "X": CharacterGender.UNKNOWN, "U": CharacterGender.UNKNOWN}[row["Gender"]],
                    personality=f"Also called: {', '.join(aliases)}",
                )
                characters.append(character)
                alias_character_mapping[character.name] = character
                for alias in aliases:
                    alias_character_mapping[alias.lower()] = character

        return characters, alias_character_mapping

    @staticmethod
    def load_pdnc_text_parts(book_id: str, pdnc_repo_path: Path, alias_character_mapping: dict[str, Character]) -> list[TextPart]:
        """
        Load text parts from the PDNC dataset.

        Args:
            book_id (str): The book ID to load.
            pdnc_repo_path (Path): Path to the PDNC repository.

        Returns:
            list[TextPart]: List of text parts in the book.
        """
        original_text = LoadPDNCGroundtruthComponent._load_from_file(pdnc_repo_path / "data" / book_id / "novel_text.txt")

        text_parts = []
        start = 0
        i = 0
        with open(pdnc_repo_path / "data" / book_id / "quotation_info.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                begs_ends = json.loads(row["quoteByteSpans"])
                for beg, end in begs_ends:
                    beg -= 1  # To include the quote mark at start
                    end += 1  # To include the quote mark at end
                    if beg > start:
                        # Add text between last quote and this quote
                        i += 1
                        text_parts.append(TextPart(
                            id=i,
                            text=original_text[start:beg],
                            type=TextPartType.OTHER,
                            character_identifier=None
                        ))
                        start = beg

                    # Add this quote
                    i += 1
                    text_parts.append(TextPart(
                        id=i,
                        text=original_text[beg:end],
                        type=TextPartType.QUOTE,
                        character_identifier=alias_character_mapping[row["speaker"].lower()].identifier
                    ))
                    start = end

            if start < len(original_text):
                # Add remaining text at the end
                i += 1
                text_parts.append(TextPart(
                    id=i,
                    text=original_text[start:],
                    type=TextPartType.OTHER,
                    character_identifier=None
                ))


        # Check if we parsed everything
        assert original_text == "".join([part.text for part in text_parts])
        return text_parts



ComponentsRegister.register_component("load_pdnc_book_groundtruth", LoadPDNCGroundtruthComponent)
