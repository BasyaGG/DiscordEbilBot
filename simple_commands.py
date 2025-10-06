# Простые команды для добавления в bot.py

@bot.command(name='test_poll')
async def test_poll(ctx, number: int = 100):
    """Тестовая команда рандома"""
    import random
    result = random.randint(1, number)
    await ctx.reply(f"🎲 Случайное число от 1 до {number}: **{result}**")

@bot.command(name='test_join')
async def test_join(ctx):
    """Тестовая команда подключения"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await ctx.reply(f"✅ Попытка подключения к каналу: **{channel.name}**")
        try:
            await channel.connect()
            await ctx.reply("✅ Подключился!")
        except Exception as e:
            await ctx.reply(f"❌ Ошибка: {str(e)}")
    else:
        await ctx.reply("❌ Вы не в голосовом канале!")

@bot.command(name='test_radio')
async def test_radio(ctx):
    """Тестовая команда радио"""
    if ctx.voice_client:
        await ctx.reply("📻 Попытка включения радио Bluford...")
        try:
            url = "http://bluford.torontocast.com:8085/stream/"
            source = discord.FFmpegPCMAudio(url)
            ctx.voice_client.play(source)
            await ctx.reply("✅ Радио включено!")
        except Exception as e:
            await ctx.reply(f"❌ Ошибка радио: {str(e)}")
    else:
        await ctx.reply("❌ Сначала подключитесь к голосовому каналу командой !test_join")