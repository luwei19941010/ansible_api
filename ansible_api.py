import shutil,json
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
from ansible import context
import ansible.constants as C

class ResultCallback(CallbackBase):
    def __init__(self,*args,**kwargs):
        # super().__init__(*args,**kwargs)
        super(ResultCallback,self).__init__(*args,**kwargs)
        self.host_ok={}
        self.host_unreachable={}
        self.host_failed={}
        self.task_ok={}

    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()]=result

    def v2_runner_on_ok(self, result,**kwargs):
        self.host_ok[result._host.get_name()]=result

    def v2_runner_on_failed(self, result, ignore_errors=False,**kwargs):
        self.host_failed[result._host.get_name()]=result

class MyAnsible2():
    def __init__(self,connection='local',#connect mode  local mode smart ssh
                 remote_user=None,       #ssh username
                 remote_password=None,   #ssh password,use dict,key must be conn_pass
                 private_key_file=None,  #key
                 sudo=None,sudo_user=None,ask_sudo_pass=None,
                 module_path=None,       #module path
                 become=None,            #authorization
                 become_method=None,     #authorization mode ,by default sudo also can su
                 become_user=None,       #after authorization ,username
                 check=False,diff=False,
                 listhosts=None,listtasks=None,listtags=None,#list  hosts  tasks tags
                 verbosity=3,            #verbosite >=3 ,display detail info
                 syntax=None,           # check playbook but not do playbook
                 start_at_task=None,     #start running
                 inventory=None,
                 ansible_network_os=None):
        context.CLIARGS=ImmutableDict(
            connection=connection,
            remote_user=remote_user,
            # remote_password=remote_password,
            # private_key_file=None,
            sudo=sudo, sudo_user=sudo_user, ask_sudo_pass=ask_sudo_pass,
            module_path=module_path,
            become=become,
            become_method=become_method,
            become_user=become_user,
            # check=False, diff=False,
            # listhosts=None, listtasks=None, listtags=None,
            verbosity=verbosity,
            syntax=syntax,
            start_at_task=start_at_task,
            # inventory=None,
            ansible_network_os=ansible_network_os
        )

        self.inventory=inventory if inventory else 'localhost,'

        self.loader=DataLoader()

        self.inv_obj=InventoryManager(loader=self.loader,sources=self.inventory)

        self.passwords=remote_password

        self.results_callback=ResultCallback()

        self.variable_manager=VariableManager(self.loader,self.inv_obj)

    def run(self,hosts='localhost',gather_facts='no',module='ping',args='',task_time=0):

        play_source=dict(
            name='ansible-hoc',
            hosts=hosts,
            gather_facts=gather_facts,
            tasks=[
                {'action':{'module':module,'args':args},'async':task_time,'poll':0}
            ]
        )
        play=Play().load(play_source,variable_manager=self.variable_manager,loader=self.loader)


        try:
            tqm=TaskQueueManager(
                inventory=self.inv_obj,
                variable_manager=self.variable_manager,
                loader=self.loader,
                passwords=self.passwords,
                stdout_callback=self.results_callback
            )

            result=tqm.run(play)

        finally:
            if tqm is not None:
                tqm.cleanup()
            shutil.rmtree('~/.ansible/tmp',True)

    def playbook(self,playbooks):

        playbook=PlaybookExecutor(playbooks=playbooks,inventory=self.inv_obj,variable_manager=self.variable_manager,loader=self.loader,passwords=self.passwords)

        playbook._tqm._stdout_callback=self.results_callback

        result=playbook.run()

    def get_result(self):
        result_raw={'success':{},'failed':{},'unreachable':{}}

        for host,result in self.results_callback.host_ok.items():
            result_raw['success'][host]=result._result
        for host,result in self.results_callback.host_failed.items():
            result_raw['failed'][host]=result._result
        for host,result in self.results_callback.host_unreachable.items():
            result_raw['unreachable'][host]=result._result

        print(json.dumps(result_raw,indent=4))


# ansible2=MyAnsible2(remote_user='luwei',remote_password={'conn_pass':'123123'},inventory='hostslist')
# ansible2.run(hosts='linux',module='shell',args='ls')
# ansible2.get_result()



ansible2=MyAnsible2(remote_user='luwei',remote_password={'conn_pass':'luwei'},inventory='hostslist',ansible_network_os='ios')
ansible2.playbook(playbooks=['ios.yml'])
ansible2.get_result()

# ansible2=MyAnsible2(remote_user='luwei',remote_password={'conn_pass':'123123'},inventory='hostslist')
# ansible2.playbook(playbooks=['linux.yml'])
# ansible2.get_result()