import discord
import os
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio

# --- Cargar Variables de Entorno ---
load_dotenv()
DISCORD_TOKEN = os.getenv('MTM4Mzk5ODA5Mjk1MjQ2OTYxNA.GBajm1.hWPfPhOa6Kb26lrG4VAOmtoM50PDFWtCOBKLu0')
GEMINI_API_KEY = os.getenv('AIzaSyD5gykj-06qJ2a7g01U-ssUaajzkYTaHa4')

# --- Configurar Google Gemini API ---
if not GEMINI_API_KEY:
    print("Error: La clave de API de Gemini no está configurada en el archivo .env")
    exit()

genai.configure(api_key=GEMINI_API_KEY)

# Inicializar el modelo generativo
# Puedes probar con 'gemini-pro' para texto general
# O 'gemini-1.5-pro-latest' si tienes acceso a los modelos más nuevos y potentes
# Asegúrate de verificar los modelos disponibles en tu Google AI Studio
try:
    model = genai.GenerativeModel('gemini-pro')
    print("Modelo Gemini cargado: gemini-pro")
except Exception as e:
    print(f"Error al cargar el modelo Gemini: {e}")
    print("Intentando con 'gemini-1.0-pro' como alternativa...")
    try:
        model = genai.GenerativeModel('gemini-1.0-pro')
        print("Modelo Gemini cargado: gemini-1.0-pro")
    except Exception as e_alt:
        print(f"Error al cargar el modelo alternativo: {e_alt}")
        print("Asegúrate de que 'gemini-pro' o 'gemini-1.0-pro' estén disponibles para tu clave API.")
        exit()


# Diccionario para almacenar el historial de conversación por usuario/canal
# Esto es crucial para que Gemini pueda "recordar" el contexto
conversation_histories = {}

# --- Configuración de Intents de Discord ---
# Habilita los intents necesarios en el Portal de Desarrolladores de Discord
intents = discord.Intents.default()
intents.message_content = True # Permite al bot leer el contenido de los mensajes
intents.members = True       # Permite al bot acceder a la información de miembros (si es necesario)
intents.presences = True     # Permite al bot acceder a la información de presencia (si es necesario)

# Crear una instancia del cliente de Discord
# Usaremos 'discord.Client' para un control más manual del evento on_message
client = discord.Client(intents=intents)

# --- Funciones Auxiliares para Gemini ---

async def get_gemini_response(user_id, channel_id, prompt):
    """
    Obtiene una respuesta de Gemini, manteniendo el historial de conversación.
    """
    chat_key = (user_id, channel_id) # Usar una tupla como clave para el historial

    if chat_key not in conversation_histories:
        # Si no hay historial, inicia una nueva conversación con el modelo
        conversation_histories[chat_key] = model.start_chat(history=[])
        print(f"Nueva conversación iniciada para {chat_key}")

    chat_session = conversation_histories[chat_key]

    try:
        # Envía el mensaje al modelo y obtiene la respuesta
        response = await asyncio.to_thread(chat_session.send_message, prompt)
        return response.text
    except Exception as e:
        print(f"Error al interactuar con Gemini: {e}")
        # En caso de error, puedes reiniciar el historial para evitar futuros problemas
        conversation_histories[chat_key] = model.start_chat(history=[])
        return "Lo siento, tengo problemas para procesar tu solicitud en este momento. Por favor, intenta de nuevo."

# --- Eventos del Bot de Discord ---

@client.event
async def on_ready():
    """Se ejecuta cuando el bot se ha conectado a Discord."""
    print(f'Bot conectado como {client.user} (ID: {client.user.id})')
    print('----------------------------------------------------')
    await client.change_presence(activity=discord.Game(name="Charlando con la IA"))
    print('El bot está listo para entablar conversaciones!')


@client.event
async def on_message(message):
    """Se ejecuta cada vez que el bot ve un mensaje."""
    # Ignorar mensajes del propio bot para evitar bucles infinitos
    if message.author == client.user:
        return

    # Imprimir el mensaje en la consola (para depuración)
    print(f'Mensaje de {message.author} ({message.author.id}) en #{message.channel.name} ({message.channel.id}): {message.content}')

    # --- Lógica de conversación con Gemini ---
    # Puedes usar un prefijo para activar la conversación con Gemini,
    # o hacer que el bot responda a cualquier mensaje que no sea un comando explícito.
    # Usaremos un prefijo "!ai" o una mención para activarlo.

    bot_mention = f'<@{client.user.id}>'

    if message.content.lower().startswith('!ai ') or message.content.lower().startswith(bot_mention.lower()):
        # Si el mensaje comienza con '!ai ' o el bot es mencionado
        if message.content.lower().startswith('!ai '):
            prompt = message.content[len('!ai '):].strip()
        else: # Si se mencionó al bot
            prompt = message.content.lower().replace(bot_mention.lower(), '').strip()

        if not prompt: # Si solo se puso !ai o solo se mencionó sin texto
            await message.channel.send("¡Hola! ¿En qué puedo ayudarte? Usa `!ai tu pregunta` o mencióname.")
            return

        # Indicar que el bot está escribiendo
        async with message.channel.typing():
            try:
                response = await get_gemini_response(message.author.id, message.channel.id, prompt)
                # Dividir la respuesta si es muy larga para evitar errores de Discord
                if len(response) > 2000:
                    chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await message.channel.send(response)
            except Exception as e:
                print(f"Error al enviar respuesta a Discord: {e}")
                await message.channel.send("Lo siento, no pude generar una respuesta. Hubo un error.")

    # --- Comandos básicos adicionales (opcional, como en el ejemplo anterior) ---
    elif message.content.lower() == '!hola':
        await message.channel.send(f'¡Hola, {message.author.mention}! Si quieres hablar con la IA, usa `!ai` seguido de tu mensaje o mencióname.')

    elif message.content.lower() == '!reset_ia':
        # Permite reiniciar la conversación para un usuario/canal específico
        chat_key = (message.author.id, message.channel.id)
        if chat_key in conversation_histories:
            del conversation_histories[chat_key]
            await message.channel.send(f'Historial de conversación con la IA reseteado para {message.author.mention}.')
        else:
            await message.channel.send(f'No hay historial de conversación activo para resetear, {message.author.mention}.')


# Iniciar el bot
client.run(DISCORD_TOKEN)
