# Public prompt-injection evaluation data

The evaluation script fetches the **test** split of
[NeurAlchemy's Prompt Injection & Jailbreak Detection Dataset](https://huggingface.co/datasets/neuralchemy/Prompt-injection-dataset)
from Hugging Face's public dataset viewer. It pins repository revision
`7d70432dfcf47a821612cbf9d34e9d9e3ad20e75` and uses the `core` configuration.
The dataset card declares Apache-2.0; it also identifies upstream sources with
their own terms, so consult the dataset card and upstream licenses before
redistributing any examples.

Samples are processed in memory and are not written to disk, printed, sent to
an inference provider, or added to the audit ledger. Only aggregate metrics are
printed. See `backend/evaluate_public_dataset.py`.
