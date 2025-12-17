import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import os

TOKEN = os.getenv("TOKEN")
ID_CANAL = 1449997658935525457
ID_CATEGORIA_TICKETS = 1449997306765250610

ID_CARGO_GERAL = 1373609365680164874  # Cargo com acesso a todas as companhias

CANAL_BOLETINS = {
    "ROTA": 1450996140043538573,
}

CARGOS_AUTORIZADOS = {
    1449998328334123208: "ROTA",
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class BotaoBoletim(Button):
    def __init__(self):
        super().__init__(label="📝 Emitir Boletim", style=discord.ButtonStyle.secondary, custom_id="botao_emitir_boletim")

    async def callback(self, interaction: discord.Interaction):
        membro = interaction.user
        possui_cargo_geral = discord.utils.get(membro.roles, id=ID_CARGO_GERAL) is not None

        if possui_cargo_geral:
            companhias = list(CANAL_BOLETINS.keys())
        else:
            companhias = list({CARGOS_AUTORIZADOS[c.id] for c in membro.roles if c.id in CARGOS_AUTORIZADOS})

        if not companhias:
            await interaction.response.send_message("Você não tem permissão para abrir boletins.", ephemeral=True)
            return

        if len(companhias) == 1:
            await interaction.response.defer(ephemeral=True)
            await criar_ticket(interaction, companhias[0])
        else:
            view = SelectCompanhiaView(companhias, interaction)
            await interaction.response.send_message(
                "Você possui múltiplos cargos autorizados. Selecione a companhia:",
                view=view,
                ephemeral=True
            )
            view.message = await interaction.original_response()

class BoletimView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BotaoBoletim())

class SelectCompanhia(Select):
    def __init__(self, companhias, interaction_inicial):
        self.interaction_inicial = interaction_inicial
        options = [discord.SelectOption(label=c, value=c) for c in companhias]
        super().__init__(placeholder="Selecione a companhia", options=options)

    async def callback(self, interaction: discord.Interaction):
        companhia = self.values[0]
        await interaction.response.defer()
        await criar_ticket(self.interaction_inicial, companhia)

        if self.view.message:
            await self.view.message.delete()

class SelectCompanhiaView(View):
    def __init__(self, companhias, interaction):
        super().__init__(timeout=60)
        self.add_item(SelectCompanhia(companhias, interaction))
        self.message = None

async def criar_ticket(interaction: discord.Interaction, companhia: str):
    membro = interaction.user

    ticket_nome = f"boletim-{companhia.lower()}"
    guild = interaction.guild
    canal_ticket = await guild.create_text_channel(
        ticket_nome,
        category=guild.get_channel(ID_CATEGORIA_TICKETS),
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            membro: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }
    )

    try:
        msg_temp = await interaction.followup.send(
            f"🔹 Seu boletim está sendo iniciado em {canal_ticket.mention}.",
            ephemeral=True
        )
        await msg_temp.delete()
    except:
        pass

    await iniciar_boletim(canal_ticket, membro, companhia)

async def iniciar_boletim(canal, membro, companhia):
    perguntas = [
        ("🛂 | 1° PARTE SERVIÇOS DIÁRIOS:", None),
        ("📁 | 2° PARTE INSTRUÇÃO E OPERAÇÕES POLICIAIS:", None),
        ("📅 | 3° PARTE ASSUNTOS GERAIS E ADMINISTRATIVOS:", None),
        ("📋 | 4° PARTE JUSTIÇA E DISCIPLINA:", None)
    ]

    def limitar(texto):
        return texto if len(texto) <= 1024 else texto[:1021] + "..."

    respostas = []
    for titulo, _ in perguntas:
        await canal.send(f"**{titulo}**\n{membro.mention}, envie sua resposta:")

        def check(m):
            return m.author == membro and m.channel == canal

        try:
            msg = await bot.wait_for('message', check=check, timeout=600)
            respostas.append((titulo, limitar(msg.content)))
        except:
            await canal.send("Tempo esgotado. Encerrando boletim.")
            await canal.delete()
            return

    embed = discord.Embed(
        title=f"BOLETIM INTERNO | {companhia}",
        color=discord.Color.blue()
    )
    for titulo, resposta in respostas:
        embed.add_field(name=titulo, value=resposta, inline=False)

    # ✅ Aqui está a correção:
    embed.add_field(name="🖊 Assina:", value=membro.mention, inline=False)

    canal_destino_id = CANAL_BOLETINS.get(companhia)
    if canal_destino_id:
        canal_destino = canal.guild.get_channel(canal_destino_id)
        if canal_destino:
            await canal_destino.send(embed=embed)

    await canal.send("Boletim enviado com sucesso. Este ticket será fechado.")
    await canal.delete()

@bot.event
async def on_ready():
    print(f"✅ BOT BOLETIM OK conectado como {bot.user}")
    canal = bot.get_channel(ID_CANAL)

    async for msg in canal.history(limit=50):
        if msg.author == bot.user:
            try:
                await msg.delete()
            except:
                pass

    embed = discord.Embed(
        title="Segurança Pública | Sistema de Boletim Interno",
        description="Clique no botão abaixo para iniciar um boletim.",
        color=discord.Color.dark_gray()
    )

    view = BoletimView()
    await canal.send(embed=embed, view=view)
    bot.add_view(view)

bot.run(TOKEN)
