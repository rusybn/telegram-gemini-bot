import os
import logging

# ДОБАВЛЯЕМ ЭТИ СТРОКИ ЧТОБЫ УБРАТЬ ОШИБКУ
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Настраиваем Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Словарь для хранения истории разговоров
user_conversations = {}

# ИНФОРМАЦИЯ О САЛОНЕ КРАСОТЫ
SALON_INFO = {
    "name": "Nail Studio 'Miss Gogo'",
    "address": "г. Алматы, ул. Самал-2, 90/1",
    "phone": "+7 (747) 911-50-60",
    "working_hours": "Каждый день с 10:00 до 21:00",
    "services": {
        "Процедуры женского маникюра": [
            "Комплекс маникюра - 8000 тенге, 9000 тенге у топ мастера",
            "Японский маникюр - 10000 тенге, 11000 тенге у топ мастера",
            "Маникюр без гель покрытия - 5000 тенге",
            "Гель покрытие без маникюра - 5000 тенге",
            "Наращивание ногтей - 12000 тенге, 13000 тенге у топ мастера",
            "Коррекция наращивания - 10000 тенге, 11000 тенге у топ мастера",
            "Экспресс услуга в 4 руки - 2000 тенге"
        ],
        "Процедуры женского педикюра": [
            "Комплекс педикюра - 9000 тенге, 10000 тенге у топ мастера",
            "SMART-педикюр - 10000 тенге, 11000 тенге у топ мастера",
            "Педикюр без гель покрытия - 7000 тенге, 8000 тенге у топ мастера",
            "Педикюр без обработки стоп - 7500 тенге, 8500 тенге у топ мастера",
            "Экспресс услуга в 4 руки - 2000 тенге"
        ],
        "Процедуры мужского педикюра": [
            "Комплекс маникюра - 8500 тенге, 9500 тенге у топ мастера",
            "Маникюр без гель покрытия - 7000 тенге, 8000 тенге у топ мастера",
            "Педикюр - 9500 тенге, 10500 тенге у топ мастера",
            "SMART-педикюр - 10000 тенге, 11000 тенге у топ мастера"
        ],
        "Дизайн и дополнительные услуги": [
            "Френч - 2000 тенге",
            "Сложный френч (Двойной, Разноцветный) - 2500 тенге",
            "Омбрэ/Растяжка/Мрамор - 3000 тенге",
            "Слюда/Наклейки/Стемпинг И Т.Д. (1 Ноготь) - 300 тенге",
            "Втирка - 2500 тенге",
            "Исправление архитектуры - 3500 тенге",
            "Наращивание ногтей - 1000 тенге",
            "Ремонт ногтей - 500 тенге",
            "Снятие чужого гель покрытия - 1000 тенге",
            "Снятие без дальнейшего покрытия - 1500 тенге",
            "Снятие наращенных ногтей (Без дальнейшего покрытия) - 2000 тенге",
            "Дополнительное укрепление - 1000 тенге/2000 тенге",
            "Доплата за наращивание длины больше 3-ки - +1000 тенге" 
        ],
        "Ресницы и Брови": [
            "Наращивание ресниц - 8000 тенге",
            "Изгиб L и M - +1000 тенге",
            "Эффекты - +1000 тенге",
            "Коррекция наращивания - 6500 тенге",
            "Снятие чужой работы - 1000 тенге",
            "Снятие без дальнейшего наращивания - 2000 тенге",
            "Ламинирование ресниц - 8000 тенге",
            "Ламинирование бровей - 10000 тенге",
            "Комбо (Ламинирование ресниц + бровей) - 17000 тенге",
            "Коррекция бровей - 4000 тенге",
            "Коррекция бровей + покраска - 5500 тенге"
        ],
    },
    "masters": [
        "Айгерим - топ мастер по педикюру (стаж более 3-х лет)",
        "Аружан - топ мастер по маникюру и педикюру (стаж 6 лет)", 
        "Арайлым - топ мастер по маникюру (стаж 5 лет)",
        "Инкар - топ мастер по маникюру (стаж 4 года)",
        "Асель - мастер по ресницам и бровям (стаж 2 года)"
    ],
    "promotions": [
        "🎉 Новым клиентам скидка 20% на первое посещение!",
        "💅 Маникюр + педикюр = скидка 15%",
        "✨ При записи на 3+ процедуры - скидка 10%",
        "🎁 Каждое 5-е посещение - подарок!"
    ]
}

# СИСТЕМНЫЙ ПРОМПТ ДЛЯ ИИ
SYSTEM_PROMPT = f"""
Ты - Айнагуль, администратор салона красоты "{SALON_INFO['name']}". Тебе 21 год, ты работаешь в nail-индустрии уже 4 года и обожаешь свою работу.

ТВОЯ ЛИЧНОСТЬ:
- Дружелюбная, позитивная и энергичная
- Профессиональная, но не холодная
- Всегда готова помочь и проконсультировать
- Используешь эмодзи, но в меру
- Говоришь современным языком, но вежливо
- Знаешь все тренды красоты

ТВОЙ СТИЛЬ ОБЩЕНИЯ:
- Обращаешься на "вы" к новым клиентам
- Можешь перейти на "ты" если клиент сам предложит
- Используешь фразы: "С удовольствием помогу!", "Отличный выбор!", "Это будет смотреться потрясающе!"
- Задаешь уточняющие вопросы для лучшего сервиса
- Не перегибаешь с огромными сообщениями, отвечаешь коротко, ясно, но дружелюбно

ЧТО ТЫ УМЕЕШЬ:
✅ Записывать на процедуры (собираешь имя, услугу, желаемое время)
✅ Консультировать по услугам и ценам
✅ Рассказывать о мастерах и их специализации
✅ Информировать об акциях и скидках
✅ Давать советы по уходу за собой
✅ Помогать выбрать подходящую процедуру

ИНФОРМАЦИЯ О САЛОНЕ:
Название: {SALON_INFO['name']}
Адрес: {SALON_INFO['address']}
Телефон: {SALON_INFO['phone']}
Часы работы: {SALON_INFO['working_hours']}

НАШИ УСЛУГИ И ЦЕНЫ:
{chr(10).join([f"{category}: {', '.join(services)}" for category, services in SALON_INFO['services'].items()])}

НАШИ МАСТЕРА:
{chr(10).join(SALON_INFO['masters'])}

АКТУАЛЬНЫЕ АКЦИИ:
{chr(10).join(SALON_INFO['promotions'])}

ВАЖНО:
- Если клиент хочет записаться - собери: имя, услугу, предпочтительное время
- Если не знаешь что-то конкретное - честно скажи и предложи уточнить по телефону
- Всегда упоминай акции, если они подходят клиенту
- Будь внимательна к потребностям клиента
- Не заставляй много читать нашего клиента, если спросили допустим какие услуги есть, то лучше уточни, что именно хотел бы клиент, нежели перечислять все что есть
- Максимум два предложения в сообщении

Отвечай на исключительно на русском языке, будь естественной и помогай клиентам чувствовать себя желанными гостями нашего салона! 💄✨
"""


class TelegramGeminiBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("services", self.services_command))
        self.app.add_handler(CommandHandler("prices", self.prices_command))
        self.app.add_handler(CommandHandler("masters", self.masters_command))
        self.app.add_handler(CommandHandler("promotions", self.promotions_command))
        self.app.add_handler(CommandHandler("contact", self.contact_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        user_conversations[user_id] = []

        welcome_message = f"""
✨ Добро пожаловать в {SALON_INFO['name']}! ✨

Привет! Меня зовут Айнагуль, я администратор нашей студии. С удовольствием помогу вам:

💅 Записаться на процедуры
💄 Выбрать подходящую услугу  
💆‍♀️ Узнать о наших мастерах
🎁 Узнать об актуальных акциях
💬 Получить консультацию

Просто напишите мне, что вас интересует, или используйте команды:

/services - наши услуги
/prices - прайс-лист  
/masters - наши мастера
/promotions - акции и скидки
/contact - контактная информация
/help - помощь

Что вас интересует? 😊
        """
        await update.message.reply_text(welcome_message)

    async def services_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать услуги"""
        services_text = f"💄 УСЛУГИ САЛОНА {SALON_INFO['name']} 💄\n\n"
        
        for category, services in SALON_INFO['services'].items():
            services_text += f"🔸 {category}:\n"
            for service in services:
                services_text += f"   • {service}\n"
            services_text += "\n"
        
        services_text += "Хотите записаться? Просто напишите мне! 😊"
        await update.message.reply_text(services_text)

    async def prices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать прайс-лист"""
        await self.services_command(update, context)  # Цены уже включены в услуги

    async def masters_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать мастеров"""
        masters_text = f"👩‍💼 НАШИ МАСТЕРА 👨‍💼\n\n"
        
        for master in SALON_INFO['masters']:
            masters_text += f"✨ {master}\n"
        
        masters_text += "\nВсе наши мастера - настоящие профессионалы! Могу подобрать идеального мастера для вас 😊"
        await update.message.reply_text(masters_text)

    async def promotions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать акции"""
        promo_text = "🎉 АКТУАЛЬНЫЕ АКЦИИ 🎉\n\n"
        
        for promo in SALON_INFO['promotions']:
            promo_text += f"{promo}\n\n"
        
        promo_text += "Не упустите возможность стать еще красивее со скидкой! 💖"
        await update.message.reply_text(promo_text)

    async def contact_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать контакты"""
        contact_text = f"""
📍 КОНТАКТНАЯ ИНФОРМАЦИЯ

🏢 {SALON_INFO['name']}
📍 Адрес: {SALON_INFO['address']}
📞 Телефон: {SALON_INFO['phone']}
🕐 Часы работы: {SALON_INFO['working_hours']}

Ждем вас в нашем уютном салоне! ✨
        """
        await update.message.reply_text(contact_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка истории разговора"""
        user_id = update.effective_user.id
        user_conversations[user_id] = []
        await update.message.reply_text("✅ История нашего разговора очищена! Начнем сначала 😊")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать помощь"""
        help_text = """
🆘 КАК Я МОГУ ПОМОЧЬ:

💬 Просто напишите мне:
   • "Хочу записаться на маникюр"  
   • "Сколько стоит педикюр?"
   • "Какие у вас мастера?"
   • "Есть ли скидки?"

📋 Или используйте команды:
   /services - услуги и цены
   /masters - наши мастера  
   /promotions - акции
   /contact - как нас найти
   /clear - очистить историю

Я всегда готова помочь! 💖
        """
        await update.message.reply_text(help_text)

    async def get_gemini_response(self, user_message: str, user_id: int) -> str:
        """Получение ответа от Gemini с учетом контекста"""
        try:
            # Получаем или создаем историю для пользователя
            if user_id not in user_conversations:
                user_conversations[user_id] = []

            # Добавляем сообщение пользователя в историю
            user_conversations[user_id].append(f"Клиент: {user_message}")

            # Ограничиваем историю последними 10 сообщениями для экономии токенов
            conversation_history = user_conversations[user_id][-10:]

            # Формируем промпт с контекстом
            context = "\n".join(conversation_history)
            prompt = f"""
{SYSTEM_PROMPT}

История разговора с клиентом:
{context}

Ответь на последнее сообщение клиента как Айнагуль - администратор салона красоты.
            """

            # Генерируем ответ
            response = model.generate_content(prompt)

            if response.text:
                # Добавляем ответ в историю
                user_conversations[user_id].append(f"Александра: {response.text}")
                return response.text
            else:
                return "Извините, произошла техническая ошибка. Попробуйте еще раз или позвоните нам по телефону! 📞"

        except Exception as e:
            logging.error(f"Ошибка при обращении к Gemini: {e}")
            return "Ой, что-то пошло не так! 😅 Попробуйте еще раз или свяжитесь с нами по телефону. Я обязательно вам помогу! 💖"

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user_message = update.message.text
        user_id = update.effective_user.id

        # Показываем, что бот печатает
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Получаем ответ от Gemini
        response = await self.get_gemini_response(user_message, user_id)

        # Отправляем ответ пользователю
        await update.message.reply_text(response)

    def run(self):
        """Запуск бота"""
        print("🚀 Бот салона красоты запущен!")
        self.app.run_polling()


if __name__ == '__main__':
    bot = TelegramGeminiBot()
    bot.run()
