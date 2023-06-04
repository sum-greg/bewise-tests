import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from pydub import AudioSegment
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from starlette.responses import FileResponse

app = FastAPI()

# Создание подключения к базе данных
engine = create_engine("postgresql://csaazefs:5LfSVACTWkkS2rruUkRQ3xZkAbj_5KE_@rajje.db.elephantsql.com/csaazefs")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Определение модели для таблицы пользователей
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    access_token = Column(String, unique=True)


# Определение модели для таблицы аудиозаписей
class AudioRecord(Base):
    __tablename__ = "audio_records"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer)
    file_path = Column(String)


# Создание таблиц в базе данных, если они не существуют
Base.metadata.create_all(bind=engine)


# Модель запроса для создания пользователя
class CreateUserRequest(BaseModel):
    name: str


# Модель запроса для добавления аудиозаписи
class AddAudioRequest(BaseModel):
    user_id: int
    access_token: str


# POST-метод для создания пользователя
@app.post("/users/")
def create_user(request: CreateUserRequest):
    session = SessionLocal()

    existing_user = session.query(User).filter(User.name == request.name).first()
    if existing_user:
        session.close()
        raise HTTPException(status_code=400, detail="User with entered name already exists")

    new_user = User(name=request.name, access_token=str(uuid.uuid4()))
    session.add(new_user)
    session.commit()
    json_user_creds = {
        "id": new_user.id,
        "access_token": new_user.access_token
    }
    session.close()

    return json_user_creds


# POST-метод для добавления аудиозаписи
@app.post("/audio/")
async def add_audio(request: AddAudioRequest, audio_file: UploadFile = File(...)):
    user_id = request.user_id
    access_token = request.access_token

    # Проверка корректности пользовательских данных
    session = SessionLocal()
    user = (
        session.query(User)
        .filter(User.id == request.user_id)
        .filter(User.access_token == request.access_token)
        .first()
    )
    if not user:
        session.close()
        raise HTTPException(status_code=401, detail="Invalid user credentials")

    # Генерация уникального имени файла и пути сохранения
    audio_id = str(uuid.uuid4())
    wav_filename = f"{audio_id}.wav"
    mp3_filename = f"{audio_id}.mp3"
    wav_filepath = os.path.join("audio", wav_filename)
    mp3_filepath = os.path.join("audio", mp3_filename)

    # Сохранение файла WAV
    with open(wav_filepath, "wb") as f:
        f.write(await audio_file.read())

    # Преобразование файла WAV в MP3
    audio_segment = AudioSegment.from_wav(wav_filepath)
    audio_segment.export(mp3_filepath, format="mp3")

    # Здесь можно выполнить сохранение информации о записи в базе данных
    audio_record = AudioRecord(id=audio_id, user_id=user.id, file_path=mp3_filepath)
    session.add(audio_record)
    session.commit()
    response_url = f"http://host:port/record?id={audio_id}&user={user_id}"
    session.close()

    return {"download_url": response_url}


# GET-метод для доступа к аудиозаписи
@app.get("/record")
def get_audio_record(audio_record_id: str, user_id: int):
    session = SessionLocal()

    audio_record = (
        session.query(AudioRecord)
        .filter(AudioRecord.id == audio_record_id)
        .filter(AudioRecord.user_id == user_id)
        .first()
    )
    if not audio_record:
        session.close()
        raise HTTPException(status_code=400, detail="Audio record not found")

    session.close()
    return FileResponse(audio_record.file_path, media_type="audio/mpeg")
