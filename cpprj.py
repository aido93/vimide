#!/usr/bin/env python3 
import json
import os
import sys
import magic
from os.path import join, split, splitext
import subprocess

config={}
conf=sys.argv[1]
with open(conf, 'r') as fr:
    config=json.load(fr)

codegen=join(splitext(conf)[:-1])
project_name=split(codegen)[-1]

cpprj_conf='/etc/cpprj/'
os.makedirs(config['dir'], exist_ok=False)
os.chdir(config['dir'])
os.copyfile(join(cpprj_conf,'lic',config['lic']), 'LICENSE')
os.copyfile(join(cpprj_conf,'Doxyfile'), 'Doxyfile')
os.makedirs('include', exist_ok=False)
os.makedirs('src', exist_ok=False)
if config['team']['designers']:
    os.makedirs('ui', exist_ok=False)
if config['team']['testers']!='':
    os.makedirs('tests', exist_ok=False)

def form_qt_config(name, type):
    text ='CONFIG += '+type+'\n'
    text+='PROJECT '+name+'\n'
    text+='SOURCES = src/*.cpp\n'
    text+='INCLUDE_PATH += include\n'
    text+='INCLUDE_PATH += $$PWD/../deps/include\n'
    text+='LIBRARY_PATH += $$PWD/../deps/lib\n'
    with open(name+'.pro', 'w') as f:
        f.write(test)

readme='#'+split(config['dir'])[-1]+' '+config['version']+'\n\n'+config['desc']+'\n'
readme+='## Dependencies:'
for d in config['dependencies']:
    for a in d:
        name=a.split('/')
        name=[v for v in name if v]
        readme+='['+name[-1]+']('+a+')'
readme+='Please contact us:\n*'+config['maintainer_url']+'\n*'+config['maintainer_email']
with open('README.md', 'w') as fw:
    fw.write(readme)

deps_path=join(config['dir'], '..', 'deps', 'src')
os.makedirs(deps_path, exist_ok=True)
os.chdir(deps_path)

archives=[]
dirs={}
aa=[]
for d in config['dependencies']:
    for a in d:
        command=''
        if d=='git':
            command='clone'
        elif d=='svn':
            command='checkout'
        elif d=='wget':
            command='-c'
            archives.append(a.split('/')[-1])
        ps = subprocess.Popen((d, command, a['url']), stdout=subprocess.PIPE)
        ps.wait()
        output = ps.stdout.read()
        print(output+'\n')
        bb=aa
        aa=os.listdir('.')
        dirs[list(set(aa)-set(bb))[0]]=a['build']
print('All dependencies has loaded\n')

for a in archives:
    t=magic.from_file(a, mime=True).split('/')[-1]
    if t=='x-xz' or t=='x-bzip2' or t=='gzip':
        ps = subprocess.Popen(('tar', 'xf', a), stdout=subprocess.PIPE)
        ps.wait()
        output = ps.stdout.read()
        print(output+'\n')
        os.remove(a)
print('All dependencies has unpacked\n')

os.chdir('..')
os.makedirs('include', exist_ok=False)
os.makedirs('lib', exist_ok=False)
os.chdir('src')
for d, build in dirs.items():
    os.chdir(d)
    ps = subprocess.Popen((build), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    os.chdir('..')
os.chdir('..')
print('All dependencies has built')

__import__(codegen+'.make_arch')
form_qt_config(project_name, config['type'])
make_arch(tabstop=config['tabstop'], snake_case=config['snake_case'], type=config['type'])
# Other builds must be done in Jenkins
print('Building for linux... Other builds must be done in Jenkins')
def test_build():
    ps = subprocess.Popen(('qmake', '..'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    if ps.exit_code!=0:
        os._exit(1)
    ps = subprocess.Popen(('make'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    if ps.exit_code!=0:
        os._exit(1)
    for p in os.listdir('tests'):
        ps = subprocess.Popen(('tests/'+p, ), stdout=subprocess.PIPE)
        ps.wait()
        if ps.exit_code!=0:
            print('Test '+p+' is not passed. Exit')
            os._exit(1)

os.makedirs('build')
os.chdir('build')
test_build()
os.chdir('..')
os.rmdir('build')

if config['git_repo']:
    ps = subprocess.Popen(('git', 'init', '.'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'add', '.'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'remote', 'add', 'origin', config['git_repo']), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'config', '--local', 'user.name', '"'+config['team']['manager']['name']+'"'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'config', '--local', 'user.email', config['team']['manager']['email']), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'commit', '-m', '"Initial commit"'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
    ps = subprocess.Popen(('git', 'push', 'origin', 'master'), stdout=subprocess.PIPE)
    ps.wait()
    output = ps.stdout.read()
    print(output+'\n')
