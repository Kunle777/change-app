import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.tasks.models import Task
from app.tasks.schemas import TaskCreate, TaskResponse, TaskUpdate

async def create_task(db: AsyncSession, task_data: TaskCreate, user_id: uuid.UUID):
    db_task = Task(
        user_id= user_id,
        title=task_data.title,
        priority=task_data.priority,
        status=task_data.status,
        description=task_data.description,
        due_date=task_data.due_date,
        reminder_time=task_data.reminder_time,
        recurrence=task_data.recurrence
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

async def get_tasks_for_user(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(select(Task).where(Task.user_id == user_id))
    return result.scalars().all()

async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    return result.scalar_one_or_none()
    
async def update_task(db: AsyncSession, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID):
    db_task = await get_task_by_id(db, task_id, user_id)
    if not db_task:
        return None
    
    for var, value in vars(task_data).items():
        if value is not None:
            setattr(db_task, var, value)
    
    await db.commit()
    await db.refresh(db_task)
    return db_task