import os
from pypdf import PdfReader


def load_documents(base_path):
    documents = []

    for root, _, files in os.walk(base_path):
        for file in files:

            file_path = os.path.join(root, file)

            if file.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    documents.append(f.read())

            elif file.endswith(".pdf"):
                reader = PdfReader(file_path)
                text = ""

                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

                if text.strip():
                    documents.append(text)

    return documents