# from uuid import uuid1
#
# from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, func
# from sqlalchemy.orm import relationship
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy_db_connection.db import Base
#
#
# class Preference(Base):
#     __tablename__ = "preference"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True)
#     name = Column(String, unique=True, index=True)
#     slug = Column(String, unique=True, index=True)
#     is_active = Column(Boolean, default=True)
#     updated_at = Column(DateTime, server_default=func.now())
#     created_at = Column(DateTime, server_default=func.now())
#
#     course_id = relationship(
#         "Course", back_populates="preference_id"
#     )
#
#
# class Course(Base):
#     __tablename__ = "course"
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True)
#     name = Column(String, unique=True, index=True)
#     slug = Column(String, unique=True, index=True)
#     icon_image = Column(Text, nullable=True)
#     web_icon = Column(Text, nullable=True)
#     is_active = Column(Boolean, default=True)
#     updated_at = Column(DateTime, server_default=func.now())
#     created_at = Column(DateTime, server_default=func.now())
#     preference = Column(String, ForeignKey("Preference.id"))
#
#     preference_id = relationship(
#         "Preference", back_populates="preference_id"
#     )
#
#
# class Category(Base):
#     __tablename__ = "category"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True)
#     name = Column(String, unique=True, index=True)
#     slug = Column(String, unique=True, index=True)
#     icon_image = Column(Text)
#     is_active = Column(Boolean, default=True)
#     updated_at = Column(DateTime, server_default=func.now())
#     created_at = Column(DateTime, server_default=func.now())
#
#
# class CourseCategories(Base):
#     __tablename__ = "coursecategories"
#
#     id = Column(UUID(as_uuid=True), primary_key=True, index=True)
#     is_active = Column(Boolean, default=True)
#     updated_at = Column(DateTime, server_default=func.now())
#     created_at = Column(DateTime, server_default=func.now())
#     course = relationship(
#         "models.Course",
#     )
#     category = relationship("category", back_populates="course_categories")
#
#
#
