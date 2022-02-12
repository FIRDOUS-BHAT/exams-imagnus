from fastapi import APIRouter

# from courses.models import PreferenceSchema, PreferenceDB, CourseBase
from student_choices.models import StudentChoices, StudentChoice_Pydantic, StudentChoiceIn_Pydantic

router = APIRouter()


@router.post('/add_student_course', response_model=StudentChoice_Pydantic)
async def add_student_course(todo: StudentChoiceIn_Pydantic):
    obj = await StudentChoices.create(**todo.dict(exclude_unset=True))
    return await StudentChoice_Pydantic.from_tortoise_orm(obj)

