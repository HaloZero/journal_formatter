import json
import logging
import os

from config import DATA_DIR

# Keep the model cache under the project's (gitignored) data/ dir, not the repo itself,
# and not a dependency any install step is required to touch - it's pulled down on
# demand by `flask download-search-model`.
MODEL_CACHE_DIR = os.path.join(DATA_DIR, 'models')
os.environ.setdefault('HF_HOME', MODEL_CACHE_DIR)

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"

SYSTEM_PROMPT = (
	"You extract structured search filters from a question about someone's personal journal. "
	"Reply with ONLY a JSON object - no other text, no markdown fences - in exactly this shape: "
	"{\"names\": [...], \"places\": [...], \"keywords\": \"...\"}. "
	"\"names\" is a list of person names mentioned in the question. "
	"\"places\" is a list of place names mentioned in the question. "
	"\"keywords\" is the remaining important topic words, as a short string, with the names "
	"and places removed. If a key has nothing to report, use an empty list or empty string.\n\n"
	"Example:\n"
	"Question: when did I talk to Sam about Jordan?\n"
	"Answer: {\"names\": [\"Sam\", \"Jordan\"], \"places\": [], \"keywords\": \"talk\"}"
)

logger = logging.getLogger('journal.query_parser')

_pipeline = None


def is_model_downloaded():
	from huggingface_hub import snapshot_download
	try:
		snapshot_download(MODEL_ID, local_files_only=True)
		return True
	except Exception:
		return False


def download_model():
	from huggingface_hub import snapshot_download
	logger.info("Downloading search model %s into %s", MODEL_ID, MODEL_CACHE_DIR)
	snapshot_download(MODEL_ID)
	logger.info("Search model download complete")


def _get_pipeline():
	global _pipeline
	if _pipeline is None:
		if not is_model_downloaded():
			return None
		from transformers import pipeline
		logger.info("Loading search model %s", MODEL_ID)
		_pipeline = pipeline("text-generation", model=MODEL_ID, torch_dtype="auto")
	return _pipeline


def parse_query(query_text):
	"""Ask the local LLM to pull structured search filters out of a natural-language
	journal question. Returns {"names": [...], "places": [...], "keywords": "..."},
	or None if the model isn't downloaded yet or generation/parsing failed - callers
	should fall back to a non-LLM heuristic in that case."""
	pipe = _get_pipeline()
	if pipe is None:
		return None

	messages = [
		{"role": "system", "content": SYSTEM_PROMPT},
		{"role": "user", "content": query_text},
	]

	try:
		output = pipe(messages, max_new_tokens=150, do_sample=False)
		generated = output[0]['generated_text'][-1]['content']
		start, end = generated.index('{'), generated.rindex('}')
		parsed = json.loads(generated[start:end + 1])
		return {
			'names': [str(n).strip() for n in parsed.get('names', []) if str(n).strip()],
			'places': [str(p).strip() for p in parsed.get('places', []) if str(p).strip()],
			'keywords': str(parsed.get('keywords', '') or '').strip(),
		}
	except Exception:
		logger.exception("Failed to parse search query with the local LLM")
		return None
