"""Gera o mod pronto em dist/: pasta do mod, zip para o release e estrutura para a Steam Workshop.

    python build.py            # gera tudo
    python build.py --install  # gera e copia para %USERPROFILE%/Zomboid/mods (para testar)

Requer Python 3.10+, Pillow e numpy (pip install pillow numpy).
"""
import os, shutil, subprocess, sys, zipfile
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MOD_ID = 'pz3d_naturepack'
VERSION = '0.11.0'
DIST = os.path.join(ROOT, 'dist')
MOD = os.path.join(DIST, MOD_ID)
PREVIEW = os.path.join(ROOT, 'docs', 'preview_models.png')
BRAND_MODELS = ['arbusto_grande_verde', 'muda_folhosa_vermelho_out', 'muda_pinheiro', 'sebe_bola',
                'muda_folhosa_olaia_flor', 'samambaia_grande', 'grama_alta_verao', 'pedra_media_1',
                'placa_curva_dir_py', 'muda_betula_ouro_out', 'arbusto_medio_outono', 'planta_folha_larga',
                'sebe_cone', 'muda_pinheiro_neve', 'placa_pare_px']


def main():
    shutil.rmtree(MOD, ignore_errors=True)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    # previa da documentacao: uma selecao que representa cada grupo de modelos
    env = dict(os.environ, PREVIEW_COLS='6', PREVIEW_CELL='260', PREVIEW_EXACT='1', PREVIEW_ONLY=','.join([
        'arbusto_grande_verde', 'arbusto_grande_roxo', 'arbusto_medio_outono', 'moita_galhos_grande',
        'sebe_alta', 'sebe_bola', 'sebe_cone', 'muda_pinheiro', 'muda_pinheiro_neve', 'muda_folhosa_vermelho_out',
        'muda_folhosa_olaia_flor', 'muda_betula_ouro_out', 'grama_alta_verao', 'grama_media_seca', 'samambaia_grande',
        'planta_folha_larga', 'planta_alta', 'folhas_secas_0', 'pedra_media_1', 'laje_2', 'chao_grama_escura',
        'chao_terra', 'placa_westpoint_esq_esq_py', 'placa_curva_dir_py', 'placa_pare_px', 'placa_zigue_px']))
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'generator', 'make_pack.py'), MOD, PREVIEW], env=env)
    # logo, capas e banner: modelos do pack renderizados com fundo transparente
    tmp = tempfile.mkdtemp(prefix='pz3d_brand_')
    spr, tmp_mod = os.path.join(tmp, 'sprites'), os.path.join(tmp, 'mod')
    os.makedirs(spr)
    env_b = dict(os.environ, PREVIEW_SPRITES=spr, PREVIEW_FLOOR='0', PREVIEW_COLS='4', PREVIEW_CELL='600',
                 PREVIEW_EXACT='1', PREVIEW_ONLY=','.join(BRAND_MODELS))
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'generator', 'make_pack.py'), tmp_mod,
                           os.path.join(tmp, 'sheet.png')], env=env_b)
    brand = os.path.join(tmp, 'out')
    subprocess.check_call([sys.executable, os.path.join(ROOT, 'generator', 'branding.py'), spr, brand])
    for fn in ('logo.png', 'banner.png', 'cover.png'):
        shutil.copy(os.path.join(brand, fn), os.path.join(ROOT, 'docs', fn))
    shutil.copy(os.path.join(brand, 'poster.png'), os.path.join(MOD, '42', 'poster.png'))

    # zip para o release do GitHub: a pasta do mod pronta para Zomboid/mods
    zpath = os.path.join(DIST, f'{MOD_ID}-v{VERSION}.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(MOD):
            for fn in files:
                full = os.path.join(base, fn)
                z.write(full, os.path.relpath(full, DIST))
    print('zip:', zpath)

    # estrutura da Steam Workshop (subir pelo menu do jogo: Workshop > Criar/Atualizar item)
    ws = os.path.join(DIST, 'workshop', 'pz3dNaturePack')
    shutil.rmtree(ws, ignore_errors=True)
    shutil.copytree(MOD, os.path.join(ws, 'Contents', 'mods', MOD_ID))
    shutil.copy(os.path.join(brand, 'preview.png'), os.path.join(ws, 'preview.png'))   # 256x256
    shutil.rmtree(tmp, ignore_errors=True)
    print('workshop:', ws)

    if '--install' in sys.argv:
        dst = os.path.join(os.path.expanduser('~'), 'Zomboid', 'mods', MOD_ID)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(MOD, dst)
        print('instalado em', dst)


if __name__ == '__main__':
    main()
