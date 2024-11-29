# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

# Analiza dla client
a = Analysis(['client.py'],
             pathex=['Z:\\src'],
             binaries=[],
             datas=[('network_policy.csv', '.')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# Analiza dla server
b = Analysis(['server.py'],
             pathex=[
                 'Z:\\src',
                 os.path.dirname(os.path.abspath('server.py'))  # Dodanie ścieżki do katalogu z plikiem server.py
             ],
             binaries=[],
             datas=[
                 ('network_policy.csv', '.'),
                 ('logger.py', '.'),
                 ('host_info.py', '.'),
                 ('port_handler.py', '.'),
                 ('connection_handlers.py', '.')
             ],
             hiddenimports=[
                 'logger',
                 'host_info',
                 'port_handler',
                 'connection_handlers',
                 'csv',
                 'socket',
                 'platform',
                 'argparse',
                 'signal',
                 'ctypes'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# PYZ dla client
pyz_a = PYZ(a.pure, a.zipped_data,
            cipher=block_cipher)

# PYZ dla server
pyz_b = PYZ(b.pure, b.zipped_data,
            cipher=block_cipher)

# EXE dla client
exe_a = EXE(pyz_a,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='client_x86',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )

# EXE dla server
exe_b = EXE(pyz_b,
          b.scripts,
          b.binaries,
          b.zipfiles,
          b.datas,
          [],
          name='server_x86',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )