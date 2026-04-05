from .en import TEXTS as EN_TEXTS
from .id import TEXTS as ID_TEXTS

LANG = {
	"en": EN_TEXTS,
	"id": ID_TEXTS,
}


def t(key: str, _l: str = "en", **kwargs) -> str:
	text = LANG.get(_l, LANG["en"]).get(key, LANG["en"].get(key, key))
	if kwargs:
		try:
			text = text.format(**kwargs)
		except (KeyError, IndexError):
			pass
	return text
