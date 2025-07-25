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


class TelegramGeminiBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        user_conversations[user_id] = []

        welcome_message = """
🤖 Привет! Я ИИ-бот на основе Google Gemini.

Просто напишите мне любое сообщение, и я отвечу!

Доступные команды:
/start - Начать заново
/clear - Очистить историю разговора
/help - Показать помощь
        """
        await update.message.reply_text(welcome_message)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Очистка истории разговора"""
        user_id = update.effective_user.id
        user_conversations[user_id] = []
        await update.message.reply_text("✅ История разговора очищена!")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать помощь"""
        help_text = """
🔹 Отправьте любое текстовое сообщение для общения с ИИ
🔹 /clear - очистить историю разговора  
🔹 /start - перезапустить бота
🔹 /help - показать эту помощь

💡 Бот запоминает контекст разговора для более естественного общения.
        """
        await update.message.reply_text(help_text)

    async def get_gemini_response(self, user_message: str, user_id: int) -> str:
        """Получение ответа от Gemini с учетом контекста"""
        try:
            # Получаем или создаем историю для пользователя
            if user_id not in user_conversations:
                user_conversations[user_id] = []

            # Добавляем сообщение пользователя в историю
            user_conversations[user_id].append(f"Пользователь: {user_message}")

            # Ограничиваем историю последними 10 сообщениями для экономии токенов
            conversation_history = user_conversations[user_id][-10:]

            # Формируем промпт с контекстом
            context = "\n".join(conversation_history)
            prompt = f"""
Ты полезный ИИ-ассистент. Отвечай на русском языке, будь дружелюбным и информативным.

История разговора:
{context}

Ответь на последнее сообщение пользователя.
            """

            # Генерируем ответ
            response = model.generate_content(prompt)

            if response.text:
                # Добавляем ответ в историю
                user_conversations[user_id].append(f"Ассистент: {response.text}")
                return response.text
            else:
                return "Извините, не смог сгенерировать ответ. Попробуйте еще раз."

        except Exception as e:
            logging.error(f"Ошибка при обращении к Gemini: {e}")
            return "Произошла ошибка при обработке запроса. Попробуйте позже."

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
        print("🚀 Бот запущен!")
        self.app.run_polling()


if __name__ == '__main__':
    bot = TelegramGeminiBot()
    bot.run()
