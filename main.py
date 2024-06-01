import psycopg2, os, fitz, argparse

from openai import OpenAI
from os import listdir
from os.path import isfile, join
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()
client.api_key = os.environ["OPENAI_API_KEY"]
conn = psycopg2.connect(f"dbname=rag_db user={os.environ['PSQL_USERNAME']} password={os.environ['PSQL_PASSWORD']} options='-c client_encoding=UTF8'")
register_vector(conn)

parser = argparse.ArgumentParser(description="Simple Python RAG Application.")
parser.add_argument('-o', '--operation', choices=['insert', 'query'], required=True, help='Specify the operation to perform: insert or query.')

def generate_embedding(text):
    response = client.embeddings.create(input=text, model="text-embedding-ada-002")
    return response.data[0].embedding

def extract_text_from_pdf(pdf_path):
    with fitz.open(pdf_path) as pdf:
        for page_num in range(pdf.page_count):
            page = pdf.load_page(page_num)
            yield page_num, page.get_text()

def insert_documents():
    cur = conn.cursor()
    directory = "documents/"
    documents = [f for f in listdir(directory) if isfile(join(directory, f))]
    for doc in documents:
        path = join(directory, doc)
        print(f"Inserting {path}...")
        is_pdf = doc.split(".")[1] == "pdf"
        if is_pdf:
            print("Is PDF")
            for page_num, page_text in extract_text_from_pdf(path):
                print(f"Generating embedding for page {page_num}")
                embedding = generate_embedding(page_text)
                cur.execute(
                    "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                    (f"Page {page_num+1} of {doc}: {page_text}", embedding)
                )
        else: 
            print("Is Not PDF")
            with open(path) as file:
                    for line_num, line in enumerate(file):
                        print(f"Generating embedding for line {line_num}")
                        embedding = generate_embedding(line)
                        cur.execute(
                            "INSERT INTO documents (content, embedding) VALUES (%s, %s)",
                            (f"Line {line_num+1} of {doc}: {line}", embedding)
                        )
    conn.commit()
    cur.close()

def query_db(query=None):
    if not query: query=input("Enter a query: ")
    cur = conn.cursor()
    query_embedding = generate_embedding(query)
    cur.execute("""
    SELECT content, embedding <-> %s::vector AS distance
    FROM documents
    ORDER BY distance ASC
    LIMIT 5
    """, (query_embedding,))
    results = cur.fetchall()
    cur.close()
    context = " ".join([row[0] for row in results])
    prompt = f"Context: {context}\n\nQ: {query}\nA:"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
        ]
    )
    print(response.choices[0].message.content)
    
args = parser.parse_args()

if args.operation == 'insert':
    insert_documents()
elif args.operation == 'query':
    query_db()