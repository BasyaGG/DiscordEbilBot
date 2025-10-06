import discord
from discord.ext import commands
import random

# Простой тест команд
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Тестовый бот готов: {bot.user}')

@bot.command(name='test_poll')
async def test_poll(ctx, number: int = 100):
    """Тестовая команда poll"""
    result = random.randint(1, number)
    await ctx.reply(f"🎲 Случайное число от 1 до {number}: **{result}**")

@bot.command(name='test_music')
async def test_music(ctx):
    """Тестовая команда музыки"""
    await ctx.reply("🎵 Музыкальные команды пока в разработке!")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Токен не найден!")