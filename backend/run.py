import uvicorn # type: ignore 
if __name__ == '__main__':
    uvicorn.run("app.main:app", host="localhost", port=3030, reload=True)
    