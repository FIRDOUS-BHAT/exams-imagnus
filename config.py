import os
from configs.connection import DATABASE_URL

DATABASE_URL = DATABASE_URL()


TORTOISE_ORM = {
    'connections': {'default': DATABASE_URL},
    'apps': {
        'models': {
            'models': [
                'admin_dashboard.models',
                'student.models',
                'student_choices.models',
                'screen_banners.models',
                'checkout.models',
                'send_mails.models',
                'study_material.models',
                'scholarship_tests.models',
                'aerich.models',  # **Important for Aerich**
            ],
            'default_connection': 'default',
        }
    },
    'use_tz': True,
    'timezone': 'Asia/Kolkata',
}
