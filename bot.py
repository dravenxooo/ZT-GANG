"""
ZT - Zéro Tolérance | Bot Discord
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("zt-bot")

TOKEN = os.environ.get("DISCORD_TOKEN")
GUILD_ID = os.environ.get("GUILD_ID")
GANG_NAME = os.environ.get("GANG_NAME", "ZT - Zéro Tolérance")
ACCENT = 0xE10600

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


def zt_embed(title, description="", color=ACCENT):
    e = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
    e.set_footer(text=f"{GANG_NAME} • Zéro Tolérance")
    return e


def is_staff():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.kick_members:
            return True
        await interaction.response.send_message(
            embed=zt_embed("Accès refusé", "Tu n'as pas les permissions.", 0xff0000), ephemeral=True
        )
        return False
    return app_commands.check(predicate)


@bot.event
async def on_ready():
    log.info(f"Connecté en tant que {bot.user}")
    try:
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            log.info(f"{len(synced)} commandes sync sur serveur {GUILD_ID}")
        else:
            synced = await bot.tree.sync()
            log.info(f"{len(synced)} commandes globales sync (peut prendre 1h)")
    except Exception as e:
        log.exception(f"Erreur sync: {e}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"sur {GANG_NAME}"),
        status=discord.Status.dnd,
    )


@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.find(
        lambda c: c.name in ("bienvenue", "welcome", "général", "general", "accueil"),
        member.guild.text_channels,
    )
    if channel and channel.permissions_for(member.guild.me).send_messages:
        embed = zt_embed(
            f"Bienvenue dans {GANG_NAME}",
            f"Salut {member.mention} ! Lis les **/regles**.\nTu es le **{member.guild.member_count}ème** membre.",
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


@bot.tree.command(name="dmall", description="Envoie un MP à tous les membres (Staff)")
@app_commands.describe(message="Message à envoyer", role="Optionnel: limiter à un rôle", inclure_bots="Inclure les bots")
@is_staff()
async def dmall(interaction: discord.Interaction, message: str, role: discord.Role | None = None, inclure_bots: bool = False):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    targets = role.members if role else guild.members
    if not inclure_bots:
        targets = [m for m in targets if not m.bot]
    targets = [m for m in targets if m.id != bot.user.id]

    if not targets:
        await interaction.followup.send(embed=zt_embed("Aucune cible", "Personne à contacter.", 0xff0000), ephemeral=True)
        return

    embed_dm = zt_embed(f"📨 Message de {GANG_NAME}", message)
    embed_dm.add_field(name="Envoyé par", value=interaction.user.mention, inline=True)
    embed_dm.add_field(name="Serveur", value=guild.name, inline=True)

    sent, failed, failed_names = 0, 0, []
    progress = await interaction.followup.send(
        embed=zt_embed("Envoi en cours...", f"0 / {len(targets)} traités"), ephemeral=True
    )
    for i, member in enumerate(targets, start=1):
        try:
            await member.send(embed=embed_dm)
            sent += 1
        except (discord.Forbidden, discord.HTTPException):
            failed += 1
            failed_names.append(member.display_name)
        await asyncio.sleep(1.2)
        if i % 10 == 0 or i == len(targets):
            try:
                await progress.edit(embed=zt_embed("Envoi en cours...",
                    f"**{i} / {len(targets)}**\n✅ {sent}\n❌ {failed}"))
            except discord.HTTPException:
                pass

    result = zt_embed("✅ Envoi terminé", f"**{sent}** MP envoyés\n**{failed}** échecs")
    if failed_names and failed <= 20:
        result.add_field(name="Échecs", value=", ".join(failed_names[:20]), inline=False)
    await interaction.followup.send(embed=result, ephemeral=True)


@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(membre="Membre", raison="Raison")
@is_staff()
async def ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("Permission ban manquante.", ephemeral=True)
        return
    try:
        await membre.ban(reason=f"{interaction.user} - {raison}")
        await interaction.response.send_message(embed=zt_embed("🔨 Banni", f"{membre.mention}\n**Raison:** {raison}"))
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.describe(membre="Membre", raison="Raison")
@is_staff()
async def kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Non spécifiée"):
    try:
        await membre.kick(reason=f"{interaction.user} - {raison}")
        await interaction.response.send_message(embed=zt_embed("👢 Expulsé", f"{membre.mention}\n**Raison:** {raison}"))
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="mute", description="Rendre muet (timeout)")
@app_commands.describe(membre="Membre", minutes="Durée en min (max 40320)", raison="Raison")
@is_staff()
async def mute(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Non spécifiée"):
    if minutes < 1 or minutes > 40320:
        await interaction.response.send_message("Durée: 1 à 40320 min.", ephemeral=True)
        return
    try:
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await membre.timeout(until, reason=f"{interaction.user} - {raison}")
        await interaction.response.send_message(embed=zt_embed("🔇 Mute", f"{membre.mention} muet **{minutes} min**\n**Raison:** {raison}"))
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="unmute", description="Retirer le mute")
@app_commands.describe(membre="Membre")
@is_staff()
async def unmute(interaction: discord.Interaction, membre: discord.Member):
    try:
        await membre.timeout(None, reason=f"Unmute par {interaction.user}")
        await interaction.response.send_message(embed=zt_embed("🔊 Unmute", f"{membre.mention} peut reparler."))
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="clear", description="Supprimer X messages (1-100)")
@app_commands.describe(nombre="Nombre de messages")
@is_staff()
async def clear(interaction: discord.Interaction, nombre: int):
    if nombre < 1 or nombre > 100:
        await interaction.response.send_message("1 à 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"🧹 {len(deleted)} messages supprimés.", ephemeral=True)


@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(membre="Membre", raison="Raison")
@is_staff()
async def warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await interaction.response.send_message(embed=zt_embed("⚠️ Warn", f"{membre.mention}\n**Raison:** {raison}"))
    try:
        await membre.send(embed=zt_embed("⚠️ Avertissement", f"Warn sur **{interaction.guild.name}**\n**Raison:** {raison}", 0xffaa00))
    except discord.Forbidden:
        pass


@bot.tree.command(name="annonce", description="Annonce officielle ZT")
@app_commands.describe(titre="Titre", message="Contenu", salon="Salon de destination")
@is_staff()
async def annonce(interaction: discord.Interaction, titre: str, message: str, salon: discord.TextChannel | None = None):
    target = salon or interaction.channel
    embed = zt_embed(f"📢 {titre}", message)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    await target.send(content="@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(everyone=True))
    await interaction.response.send_message(f"Annonce postée dans {target.mention}", ephemeral=True)


@bot.tree.command(name="regles", description="Règlement du gang ZT")
async def regles(interaction: discord.Interaction):
    embed = zt_embed(f"📜 Règlement {GANG_NAME}", "Respect du règlement **non négociable**. Zéro Tolérance.")
    embed.add_field(name="1️⃣ Respect", value="Pas d'insulte entre membres.", inline=False)
    embed.add_field(name="2️⃣ Discrétion", value="Ce qui se passe dans ZT reste dans ZT.", inline=False)
    embed.add_field(name="3️⃣ Loyauté", value="Pas de trahison, pas de double allégeance.", inline=False)
    embed.add_field(name="4️⃣ Présence", value="Réponds aux appels et opérations.", inline=False)
    embed.add_field(name="5️⃣ Hiérarchie", value="Respect du chef et des lieutenants.", inline=False)
    embed.add_field(name="⚠️ Sanction", value="warn → mute → kick → ban.", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="recrue", description="Officialiser un nouveau membre")
@app_commands.describe(membre="Nouveau", role="Rôle ZT")
@is_staff()
async def recrue(interaction: discord.Interaction, membre: discord.Member, role: discord.Role):
    try:
        await membre.add_roles(role, reason=f"Recrutement par {interaction.user}")
        embed = zt_embed("🆕 Nouvelle recrue", f"Bienvenue à {membre.mention} dans **{GANG_NAME}** !\nRôle : {role.mention}")
        embed.set_thumbnail(url=membre.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="promotion", description="Promouvoir un membre")
@app_commands.describe(membre="Membre", nouveau_role="Nouveau rôle", ancien_role="Ancien rôle (optionnel)")
@is_staff()
async def promotion(interaction: discord.Interaction, membre: discord.Member, nouveau_role: discord.Role, ancien_role: discord.Role | None = None):
    try:
        await membre.add_roles(nouveau_role, reason=f"Promotion par {interaction.user}")
        if ancien_role and ancien_role in membre.roles:
            await membre.remove_roles(ancien_role)
        await interaction.response.send_message(embed=zt_embed("⬆️ Promotion", f"{membre.mention} monte en grade !\nNouveau rôle : {nouveau_role.mention}"))
    except discord.Forbidden:
        await interaction.response.send_message("Permission insuffisante.", ephemeral=True)


@bot.tree.command(name="membres", description="Stats du serveur")
async def membres(interaction: discord.Interaction):
    g = interaction.guild
    humans = sum(1 for m in g.members if not m.bot)
    bots = sum(1 for m in g.members if m.bot)
    await interaction.response.send_message(embed=zt_embed(f"👥 {g.name}", f"**Total:** {g.member_count}\n**Humains:** {humans}\n**Bots:** {bots}"))


@bot.tree.command(name="rapport", description="Envoyer un rapport au staff")
@app_commands.describe(sujet="Sujet", details="Détails")
async def rapport(interaction: discord.Interaction, sujet: str, details: str):
    salon = discord.utils.find(lambda c: c.name in ("rapports", "staff", "logs", "rapport"), interaction.guild.text_channels)
    if not salon:
        await interaction.response.send_message("Aucun salon `#rapports` trouvé.", ephemeral=True)
        return
    embed = zt_embed(f"📝 Rapport: {sujet}", details, 0xffaa00)
    embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Par", value=interaction.user.mention)
    await salon.send(embed=embed)
    await interaction.response.send_message("Rapport envoyé.", ephemeral=True)


@bot.tree.command(name="help", description="Liste des commandes ZT")
async def help_cmd(interaction: discord.Interaction):
    embed = zt_embed(f"🤖 Commandes {GANG_NAME}", "Toutes les commandes disponibles :")
    embed.add_field(name="📨 Communication", value="`/dmall` `/annonce` `/rapport`", inline=False)
    embed.add_field(name="🔨 Modération", value="`/ban` `/kick` `/mute` `/unmute` `/warn` `/clear`", inline=False)
    embed.add_field(name="👥 Gang", value="`/recrue` `/promotion` `/regles` `/membres`", inline=False)
    embed.set_footer(text="ZT - Zéro Tolérance | Respect ou rien")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        return
    log.exception(f"Erreur commande: {error}")
    try:
        msg = f"Erreur: `{error}`"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN manquant.")
    bot.run(TOKEN, log_handler=None)
