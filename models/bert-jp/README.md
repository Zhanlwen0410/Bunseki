Place your local Japanese BERT files in this directory.

Expected HuggingFace-compatible local files include:
- config.json
- tokenizer_config.json
- vocab.txt (or tokenizer.json)
- pytorch_model.bin (or model.safetensors)

This project loads the model with `local_files_only=True` and does not access network.
