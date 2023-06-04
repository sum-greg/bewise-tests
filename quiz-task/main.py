import requests
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

app = FastAPI()

# Создание подключения к базе данных
engine = create_engine("postgresql://csaazefs:5LfSVACTWkkS2rruUkRQ3xZkAbj_5KE_@rajje.db.elephantsql.com/csaazefs")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# Определение модели для таблицы вопросов
class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String)
    answer_text = Column(String)
    created_at = Column(DateTime, default=datetime.now)


# Создание таблицы в базе данных, если она не существует
Base.metadata.create_all(bind=engine)


# Модель запроса с количеством вопросов
class QuestionRequest(BaseModel):
    questions_num: int


# POST-метод для получения вопросов
@app.post("/questions/")
def get_questions(request: QuestionRequest):
    session = SessionLocal()

    questions = []
    while len(questions) < request.questions_num:
        response = requests.get("https://jservice.io/api/random?count=1")
        data = response.json()
        question_data = data[0]

        existing_question = (
            session.query(Question)
            .filter(Question.question_text == question_data["question"])
            .first()
        )

        if existing_question:
            continue

        question = Question(
            question_text=question_data["question"],
            answer_text=question_data["answer"],
        )
        session.add(question)
        session.commit()
        json_question = {
            "id": question.id,
            "question_text": question.question_text,
            "answer_text": question.answer_text,
            "created_at": question.created_at
        }
        questions.append(json_question)

    session.close()

    return questions[-1]
