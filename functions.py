import re
from difflib import SequenceMatcher
from header_detection import subtypes_autodetection

constructor_post_mod = ['=delete', '=0', '=default', 'noexcept']
pre_func_modifiers     = [  'static', 'inline', 'extern']
post_func_modifiers    = []
pre_method_modifiers   = [  'static', 'virtual', 'friend']
post_method_modifiers  = [  '=0', '=delete', '=default', 'const', 'const =0', 'const =delete', 'volatile', 
                            'const volatile', 'noexcept', 'override', 'final', '&', '&&']
class arg:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    pre_modifier=None
    type=None
    name=''
    value=None
    def __str__(self):
        if self.type=='void':
            return 'void'
        a=''
        if self.pre_modifier:
            a+=self.pre_modifier+' '
        a+=(self.type+' '+self.name)
        if self.value:
            a+=('='+self.value)
        return a

class method:
    template_args=[]
    pre_modifier=None
    return_type=None
    class_name=''
    name=''
    args=[]
    post_modifier=None
    body=None
    hint=''
    logger=True
    autodetected=[]
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        if self.pre_modifier:
            if self.pre_modifier in pre_method_modifiers:
                if self.name==self.class_name:
                    raise Exception("constructor cannot have pre-modifiers")
            else:
                raise Exception("Undefined pre-modifier: "+str(self.pre_modifier))
        if self.return_type and self.name==self.class_name:
                raise Exception("constructor cannot have type")
        if self.post_modifier:
            if self.post_modifier in post_method_modifiers:
                if self.name==self.class_name and self.post_modifier not in constructor_post_mod:
                    raise Exception("constructor cannot be "+str(self.post_modifier))
            else:
                raise Exception("Undefined post-modifier: "+str(self.post_modifier))
        if 'return_type' in kwargs:
            self.return_type=kwargs['return_type'].rstrip()
        types=[]
        types.append(self.return_type)
        if self.args:
            for i in self.args:
                types.append(i.type)
        self.autodetected=subtypes_autodetection(types)
    
    def decl(self):
        a=''
        i=1
        if self.args:
            for x in self.args:
                a+=str(x)
                if i<len(self.args):
                    a+=', '
                i=i+1
        ret=''
        if self.template_args:
            ret+='template <class '+', class '.join(self.template_args)+'>\n'
        if self.pre_modifier:
            ret+=self.pre_modifier+' '
        if self.return_type:
            ret+=self.return_type+' '
        ret+=self.name+' ('+a+')'
        if self.post_modifier:
            ret+=(' '+self.post_modifier)
        if self.hint=='getter' or self.hint=='setter':
            ret+='\n{ '+self.body+' }'
        else:
            ret+=';'
        return ret
    def impl(self, ts=' '*4, class_fields=None):
        ret=''
        if self.hint=='getter' or self.hint=='setter':
            return ret
        a=''
        i=1
        if self.args:
            for v in self.args:
                if v.pre_modifier:
                    a+=(v.pre_modifier+' ')
                if v.name:
                    a+=(v.type+" "+v.name)
                elif v.type=='void':
                    a+=v.type
                else:
                    a+=(v.type+" x")
                if i<len(self.args):
                    a+=', '
                i=i+1
        if self.template_args:
            ret+='template <class '+', class '.join(self.template_args)+'>\n'
        if self.pre_modifier=='static':
            ret+='static '
        if self.return_type:
            ret+=self.return_type+' '
        if self.class_name!='':
            ret+=self.class_name+'::'
        ret+=self.name+' ('+a+')'
        if self.post_modifier:
            ret+=(' '+self.post_modifier)
        def similar(a, b):
            return SequenceMatcher(None, a, b).ratio()
        if not self.return_type and class_fields and len(self.args)>0 and self.name[0]!='~' and self.hint!='copy' and self.hint!='move':
            initer={}
            for ar in self.args:
                for p in class_fields:
                    if similar(ar.name, p.name)>=0.8:
                        initer[p]=ar
            if initer:
                ret+=' : \n'+ts*2
                i=1
                for key, value in initer.items():
                    ret+=key+'('+value+')'
                    if i<len(initer):
                        ret+=',\n'+ts*2
                    i=i+1
                ret+='\n'
        ret+='\n{\n'+ts
        nulls=['int', 'unsigned int', 'uint32_t', 'int32_t', 'long', 'unsigned long', 'ulong']
        if self.logger==True:
            ret+='logger->debug("{0}: {1} [thread %t] - Enter in function {2}", __FILE__, __LINE__, __FUNCTION__);'
        if self.body:
            ret+=self.body
        elif self.return_type and self.return_type!='void' and self.hint!='move' and self.hint!='copy':
            ret+=self.return_type+' ret'
            if '*' in self.return_type:
                ret+='=nullptr'
            elif self.return_type in nulls:
                ret+='=0'
            elif self.return_type=='bool':
                ret+='=false'
            ret+=';\n'+ts+'\n'+ts+'return ret;'
        elif self.return_type and self.hint=='copy':
            if self.args[0].name!='':
                ret+=('if (this != &'+self.args[0].name+')\n'+ts+'{\n')
            else:
                ret+=('if (this != &x)\n'+ts+'{\n')
            ret+=(ts*2+'\n'+ts+'}\n'+ts+'return *this;')
        ret+='\n}\n'
        return ret

# for generating a bunch of dummy functions
def funcs(line):
    line=line.replace('\n','')
    line=line.replace(';','; ')
    line=re.sub('\s+',' ', line)
    funcs=line.split('; ')
    funcs=[value for value in funcs if value]
    ret=[]
    for f in funcs:
        a=re.match('((?:.*)\s)+(\w+)\s*(?:<(.*?)>)?\s*\((.*?)\)(.*?)', f)
        return_type=re.sub('\s+',' ',a.group(1))
        pre=return_type.split(' ')
        if pre[0] in pre_method_modifiers or pre[0] in pre_func_modifiers:
            return_type=' '.join(pre[1:]).rstrip()
            pre=pre[0]
        else:
            pre=None
        name=a.group(2)
        template_list=a.group(3)
        if template_list:
            template_list=template_list.replace(',',', ')
            template_list=re.sub('\s+',' ', template_list)
            template_list=template_list.split(', ')
        args=a.group(4).replace(',',', ')
        if args!='':
            args=re.sub('\s+',' ', args)
            args=args.split(', ')
            new_args=[]
            t1=0
            temp=''
            for ar in args:
                c1=ar.count('<')
                c2=ar.count('>')
                t1=t1+c1-c2
                if t1<0:
                    raise Exception('Count of < is less than >')
                elif t1>0:
                    temp=temp+ar
                else:
                    a1=temp+ar
                    kv1=a1.split('=')
                    value=None
                    if len(kv1)==2:
                        type_name=kv1[0]
                        value=kv1[1]
                    else:
                        type_name=a1
                        value=None
                    if '**' not in type_name:
                        type_name=type_name.replace('*', '* ')
                    else:
                        type_name=type_name.replace('**', '** ')
                    if '&&' not in type_name:
                        type_name=type_name.replace('&', '& ')
                    else:
                        type_name=type_name.replace('&&', '&& ')
                    *type_f, var_name=type_name.split(' ')
                    if not type_f:
                        new_args.append(arg(type=var_name, value=value))
                    elif type_f[0]=='const':
                        type_f=type_f[1:]
                        new_args.append(arg(pre_modifier='const', type=' '.join(type_f), name=var_name, value=value))
                    else:
                        new_args.append(arg(type=' '.join(type_f), name=var_name, value=value))
                        
                    temp=''
        else:
            new_args=None
        #now we cannot continue because of map<int, int, str> - this cannot be parsed correctly
        post_modifier=a.group(5)
        if post_modifier!='' and not (post_modifier in post_method_modifiers or post_modifier in post_func_modifiers):
            raise Exception('Undefined post-modifier:'+post_modifier)
        ret.append(method(  template_args=template_list, 
                            pre_modifier=pre, 
                            return_type=return_type, 
                            name=name, 
                            args=new_args, 
                            post_modifier=post_modifier))
    return ret

def statics(line):
    l=funcs(line)
    for func in l:
        func.pre_modifier='static'
    return l

#TODO IT
cycles=['for', 'while', 'do']
def func_body(line, args, class_fields):
    line=line.replace('\n','')
    line=re.sub('\s+',' ', line)
    ops=line.split(' ')
    def rec(opses):
        v=opses[0]
        if v in cycles or opses=='switch':
            end=rec(opses[1:])
            return gen_code(v, end, args, class_fields, body)
        else:
            return v

def create_comments(methods):
    ret={}
    i=1
    for p in methods:
        if not(p.hint=='setter' or p.hint=='getter'):
            hpp=''
            hpp+=("/**\n * \\brief ")
            if p.return_type==None: # Constructors and destructors
                if p.hint=='copy':
                    hpp+="Copy constructor"
                elif p.hint=='move':
                    hpp+="Move constructor"
                elif p.name[0]=='~':
                    hpp+="Destructor"

                if p.post_modifier=='=delete':
                    hpp+=" is deleted because "
                elif p.post_modifier=='=default':
                    hpp+=" is default"
                hpp+=('\n * \\details \n')
    
                if p.args and p.hint!='copy' and p.hint!='move':
                    for a in p.args:
                        hpp+=(" * \\param[in] "+a.name+' - \n')

                if p.hint=='copy':
                    hpp+=(" * \\return Copy of object\n")
                elif p.hint=='move':
                       hpp+=(" * \\return Rvalue-reference to the object\n")
            else:
                if p.hint=='copy':
                    hpp+=("Copy operator=")
                elif p.hint=='move':
                    hpp+=("Move operator=")
            
                if p.post_modifier=='=delete':
                       hpp=hpp+" is deleted because "
                elif p.post_modifier=='=default':
                    hpp=hpp+" is default"
                hpp+=('\n * \\details \n')
                
                if p.template_args:
                    for v in p.template_args:
                        hpp+=" * \\param [in] "+v+" is the type corresponding to \n"
                if p.args and p.hint!='copy' and p.hint!='move':
                    for v in p.args:
                        if v.type!='void':
                            hpp+=" * \\param [in] "+v.name+" - "+"."
                            if v.value:
                                hpp+=" Default value is "+v.value
                            hpp+="\n"

                if p.hint=='copy':
                    hpp+=(" * \\return Copy of object\n")
                elif p.hint=='move':
                    hpp+=(" * \\return Rvalue-reference to the object\n")
                elif p.return_type=='void':
                    hpp+=(" * \\return None \n")
                else:
                    hpp+=(" * \\return  \n")
            hpp+=(' **/\n')
            ret[i]=hpp
        i=i+1
    return ret

