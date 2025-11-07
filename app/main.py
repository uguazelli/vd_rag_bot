from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.staticfiles import StaticFiles

from .controller import rag_docs, rag_ingest, webhooks
from .controller import bot as bot_controller
from .web.views import router as web_router

app = FastAPI()

app.include_router(web_router)

static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health():
    print("🤖 Health check", flush=True)
    return {"message": "Status OK"}


@app.post("/rag/docs/{folder_name}")
async def upload_documents(folder_name: str, files: list[UploadFile] = File(...)):
    return await rag_docs.upload_documents(folder_name, files)


@app.get("/rag/docs/{folder_name}")
async def list_documents(folder_name: str):
    return rag_docs.list_documents(folder_name)


@app.get("/rag/docs/{folder_name}/{file_name}")
async def download_document(folder_name: str, file_name: str):
    return rag_docs.download_document(folder_name, file_name)


@app.delete("/rag/docs/{folder_name}")
async def delete_folder(folder_name: str):
    return rag_docs.delete_folder(folder_name)


@app.post("/rag/ingest")
async def trigger_ingest(payload: rag_ingest.IngestRequest):
    return await rag_ingest.trigger_ingest(payload)


@app.post("/chatwoot/webhook")
async def webhook(request: Request):
    payload = await request.json()
    return webhooks.process_chatwoot_webhook(payload)


@app.post("/twenty/webhook")
async def twenty_webhook(request: Request):
    payload = await request.json()
    return webhooks.process_twenty_webhook(payload)


@app.post("/bot")
async def bot_endpoint(request: Request):
    data = await request.json()
    return await bot_controller.process_bot_request(data)
