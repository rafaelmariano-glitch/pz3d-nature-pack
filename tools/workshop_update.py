"""Atualiza o item da Steam Workshop pela Steam ja logada, sem abrir o jogo.

    python tools/workshop_update.py <pasta_do_item> "nota da mudanca"   # envia capa e conteudo
    python tools/workshop_update.py <pasta_do_item> --require 3807334881 3619862853
                                                                        # marca itens obrigatorios

A pasta e a que o jogo usa (Zomboid/Workshop/<nome>): precisa de workshop.txt com id=,
preview.png e Contents/. Usa o steam_api64.dll do Project Zomboid (app 108600).
So funciona para o dono do item, com o cliente da Steam aberto e logado.
"""
import ctypes as C, os, shutil, sys, tempfile, time

APP = 108600
DLL = r'C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\steam_api64.dll'
STATUS = {0: 'concluido', 1: 'preparando', 2: 'preparando conteudo', 3: 'enviando conteudo',
          4: 'enviando capa', 5: 'gravando'}


class Steam:
    def __init__(self):
        work = tempfile.mkdtemp(prefix='ws_')     # a Steam le steam_appid.txt da pasta atual
        shutil.copy(DLL, work)
        open(os.path.join(work, 'steam_appid.txt'), 'w').write(str(APP))
        os.chdir(work)
        self.api = api = C.CDLL(os.path.join(work, 'steam_api64.dll'))
        err = C.create_string_buffer(1024)
        api.SteamAPI_InitFlat.restype = C.c_int
        r = api.SteamAPI_InitFlat(err)
        if r != 0:
            sys.exit(f'Steam nao iniciou ({r}): {err.value.decode(errors="replace")}')
        api.SteamAPI_SteamUGC_v021.restype = C.c_void_p
        api.SteamAPI_SteamUtils_v010.restype = C.c_void_p
        self.ugc, self.utils = api.SteamAPI_SteamUGC_v021(), api.SteamAPI_SteamUtils_v010()

    def fn(self, name, res, *args):
        f = getattr(self.api, 'SteamAPI_' + name)
        f.restype, f.argtypes = res, [C.c_void_p] + list(args)
        return f

    def wait(self, call, struct, cb_id, tick=None):
        done = self.fn('ISteamUtils_IsAPICallCompleted', C.c_bool, C.c_uint64, C.POINTER(C.c_bool))
        failed = C.c_bool(False); t0 = time.time()
        while not done(self.utils, call, C.byref(failed)):
            self.api.SteamAPI_RunCallbacks()
            if tick: tick()
            if time.time() - t0 > 900: sys.exit('tempo esgotado')
            time.sleep(0.5)
        res = struct()
        get = self.fn('ISteamUtils_GetAPICallResult', C.c_bool, C.c_uint64, C.c_void_p, C.c_int, C.c_int,
                      C.POINTER(C.c_bool))
        get(self.utils, call, C.byref(res), C.sizeof(res), cb_id, C.byref(failed))
        return res

    def close(self):
        self.api.SteamAPI_Shutdown()


class SubmitResult(C.Structure):      # SubmitItemUpdateResult_t (3404)
    _fields_ = [('result', C.c_int), ('needs_legal', C.c_bool), ('item', C.c_uint64)]


class DependencyResult(C.Structure):  # AddUGCDependencyResult_t (3412)
    _fields_ = [('result', C.c_int), ('parent', C.c_uint64), ('child', C.c_uint64)]


def upload(st, item, folder, note):
    h = st.fn('ISteamUGC_StartItemUpdate', C.c_uint64, C.c_uint32, C.c_uint64)(st.ugc, APP, item)
    for name, val in (('SetItemContent', 'Contents'), ('SetItemPreview', 'preview.png')):
        path = os.path.abspath(os.path.join(folder, val)).encode('utf-8')
        if not st.fn('ISteamUGC_' + name, C.c_bool, C.c_uint64, C.c_char_p)(st.ugc, h, path):
            sys.exit(name + ' falhou')
    call = st.fn('ISteamUGC_SubmitItemUpdate', C.c_uint64, C.c_uint64, C.c_char_p)(st.ugc, h, note.encode('utf-8'))
    prog = st.fn('ISteamUGC_GetItemUpdateProgress', C.c_int, C.c_uint64, C.POINTER(C.c_uint64), C.POINTER(C.c_uint64))
    a, b, last = C.c_uint64(), C.c_uint64(), [None]

    def tick():
        msg = f'{STATUS.get(prog(st.ugc, h, C.byref(a), C.byref(b)), "?")} {a.value}/{b.value}'
        if msg != last[0]: print(msg, flush=True); last[0] = msg
    res = st.wait(call, SubmitResult, 3404, tick)
    print(f'resultado={res.result} (1 = OK)  precisa_aceitar_acordo={res.needs_legal}')
    return res.result == 1


def require(st, item, children):
    add = st.fn('ISteamUGC_AddDependency', C.c_uint64, C.c_uint64, C.c_uint64)
    ok = True
    for child in children:
        res = st.wait(add(st.ugc, item, child), DependencyResult, 3412)
        print(f'obrigatorio {child}: resultado={res.result} (1 = OK)')
        ok &= res.result == 1
    return ok


def main(argv):
    folder = os.path.abspath(argv[0])
    meta = dict(l.split('=', 1) for l in open(os.path.join(folder, 'workshop.txt'), encoding='utf-8').read().splitlines() if '=' in l)
    item = int(meta['id'])
    st = Steam()
    try:
        if len(argv) > 1 and argv[1] == '--require':
            ok = require(st, item, [int(x) for x in argv[2:]])
        else:
            ok = upload(st, item, folder, argv[1] if len(argv) > 1 else 'Update')
    finally:
        st.close()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
