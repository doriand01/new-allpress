from bs4 import BeautifulSoup as Soup
from sentence_transformers import SentenceTransformer as Model

import regex
import spacy


nlprocessor = spacy.load('xx_ent_wiki_sm')


class Article:

    def _extract_text(self):
        paragraphs = self.html.find_all('p')
        text = ' '.join([p.get_text() for p in paragraphs])
        return text.strip()

    def _rhetorical_mask(self):
        tokens = []
        for token in self.document:
            if token.ent_type_:
                tokens.append(' UNK ')
            else:
                tokens.append(token.text_with_ws)
        return ''.join(tokens)

    def _semantic_mask(self):
        masked_doc = ' '.join(self.entities)
        return masked_doc



    def __init__(self,
                 url: str,
                 content: Soup):

        self.url = url
        self.html = content
        self.document = nlprocessor(self._extract_text())
        self.doc_text = self.document.text
        self.entities = [ent.text for ent in self.document.ents]
        self.entity_string = ' '.join(self.entities)
        self.rhetoric = self._rhetorical_mask()
        self.semantic = self._semantic_mask()