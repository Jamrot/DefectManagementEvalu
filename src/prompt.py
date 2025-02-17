import os
import json
import tokens
import random
from tqdm import tqdm

def generate_prompt(root, task, dataset, method, max_tokens = 8000, TEST = 'vali', testNum = 1):
    if TEST=='test':
        data_file = os.path.join(root, task, dataset+'-test.json')
    elif TEST=='vali':
        data_file = os.path.join(root, task, dataset+'-validation.json')
    elif TEST=='remain':
        data_file = os.path.join(root, task, dataset+'-remain.json')
    else:
        print('please input the right TEST!')
        exit()
    
    prompt_file = os.path.join(root, task, dataset+'-prompt.json')
    if not os.path.exists(prompt_file):
        prompt_file = os.path.join(root, task, task+'-prompt.json')
    with open(prompt_file) as f:
        prompt = json.load(f)

    with open(data_file) as f:
        data = json.load(f)

    if dataset in data:
        data = data[dataset]
    else:
        print('illegal dataset!')
        exit()
    
    if method in prompt:
        prompt = prompt[method]
    else:
        print('illegal method!')
        print(prompt.keys())
        exit()
    
    prompts = []
    prompt_item_num = 0
    for id in tqdm(data):
        if prompt_item_num>testNum:
            break
        prompt_item = prompt[:-1]
        
        if dataset=='title_itape':
            clonze = data[id]['bug_report']
            if method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                for nshot_id in nshot_data:
                    nshot_clonze = '\n'.join(['Bug report: '+nshot_data[nshot_id]['bug_report']])
                    ground_truth = nshot_data[nshot_id]['ground_truth']
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
        
        elif dataset=='Chromium':
            if method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                # nshot_message = []
                for nshot_id in nshot_data:
                    nshot_clonze = '\n'.join(['Bug report: '+nshot_data[nshot_id]['bug_report']])
                    key_list = ["non-security bug report", "security bug report"]
                    ground_truth = key_list[int(nshot_data[nshot_id]['ground_truth'])]
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            else:
                clonze = data[id]['bug_report']
        
        elif dataset=='stable_patchnet':
            if method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                # nshot_message = []
                for nshot_id in nshot_data:
                    nshot_clonze = 'Patch: '+ nshot_data[nshot_id]['patch']
                    if nshot_data[nshot_id]['ground_truth']=='true':
                        ground_truth = 'ACK'
                    else:
                        ground_truth = 'NAK'
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            elif method=='few-shot':
                clonze = '\n'.join([data[id]['title'], data[id]['message_xtrailer'], data[id]['diff']])
            else:
                clonze = data[id]['patch']
        
        elif dataset=='APCA_quatrain':
            if method=='info-manual':
                bug_description = data[id]['bug_description']
                token_test_message = {'role':'user', 'content':bug_description}        
                if tokens.num_tokens_from_messages([token_test_message])>max_tokens//2:
                    print('bug report processing ({} tokens): {}'.format(max_tokens//2, id))
                    bug_description = tokens.message_process(token_test_message, max_tokens//2)['content']
                clonze = '\n'.join([
                    'Bug report: ', 
                    data[id]['bug_summary'], 
                    bug_description,
                    'Patch: ', 
                    data[id]['patch_description'], 
                    # data[id]['patch_code']
                    ])
            elif method=='info-gpt':
                bug_description = data[id]['bug_description']
                patch_description = data[id]['patch_description']
                token_test_message = {'role':'user', 'content':bug_description}        
                if tokens.num_tokens_from_messages([token_test_message])>max_tokens//2:
                    print('bug report processing ({} tokens): {}'.format(max_tokens//2, id))
                    bug_description = tokens.message_process(token_test_message, max_tokens//2)['content']
                clonze = '\n'.join([
                    'Bug report: ', 
                    data[id]['bug_summary'], 
                    bug_description,
                    'Patch: ', 
                    patch_description, 
                    # data[id]['patch_code']
                    ])
            elif method=='info-code':
                bug_description = data[id]['bug_description']
                patch_description = data[id]['patch_description_gpt']
                token_test_message = {'role':'user', 'content':bug_description}        
                if tokens.num_tokens_from_messages([token_test_message])>max_tokens//2:
                    print('bug report processing ({} tokens): {}'.format(max_tokens//2, id))
                    bug_description = tokens.message_process(token_test_message, max_tokens//2)['content']
                clonze = '\n'.join([
                    'Bug report: ', 
                    data[id]['bug_summary'], 
                    bug_description,
                    'Patch: ', 
                    patch_description, 
                    data[id]['patch_code']
                    ])
            elif method=='code-only':
                clonze = 'Patch:\n' + data[id]['patch_code']
            elif method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                # nshot_message = []
                for nshot_id in nshot_data:
                    bug_description = nshot_data[nshot_id]['bug_summary']
                    patch = nshot_data[nshot_id]['patch_description']
                    nshot_clonze = '\n'.join([
                        'Bug report: ', bug_description,
                        'Patch: ', patch])
                    if nshot_data[nshot_id]['ground_truth']=='1':
                        ground_truth = 'CoF'
                    else:
                        ground_truth = 'NCF'
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            else:
                clonze = '\n'.join([
                    'Bug report: '+ data[id]['bug_summary'], 
                    data[id]['bug_description'],
                    'Patch: ' + data[id]['patch_description']])
        elif dataset=='APCA_panther':
            if method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                for nshot_id in nshot_data:
                    patch = nshot_data[nshot_id]['patch']
                    nshot_clonze = 'Patch:\n'+patch
                    if nshot_data[nshot_id]['ground_truth']=='Correct':
                        ground_truth = 'CoF'
                    else:
                        ground_truth = 'NCF'
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            else:
                clonze = 'Patch:\n' + data[id]['patch']
        elif dataset=='APCA_invalidator':
            if method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                for nshot_id in nshot_data:
                    patch = nshot_data[nshot_id]['patch']
                    nshot_clonze = 'Patch:\n'+patch
                    if nshot_data[nshot_id]['ground_truth']=='Correct':
                        ground_truth = 'CoF'
                    else:
                        ground_truth = 'NCF'
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            else:
                clonze = 'Patch:\n' + data[id]['patch']
        
        elif task=='cvss':
            if method=='manual-info':
                clonze = '\n'.join(['Function: '+data[id]['function'],
                                    data[id]['description']])
            elif method=='summary':
                nshot_file = os.path.join(root, task, dataset+'-nshot.json')
                with open(nshot_file) as f:
                    nshot_data = json.load(f)[dataset]
                suffle_temp = list(nshot_data.items())
                random.seed(0)
                random.shuffle(suffle_temp)
                nshot_data = dict(suffle_temp)
                # nshot_message = []
                for nshot_id in nshot_data:
                    nshot_clonze = '\n'.join(['Function: '+nshot_data[nshot_id]['function'],
                                    nshot_data[nshot_id]['description']])
                    if dataset=="AV":
                        key_list = ["Not Related", "Network", "Adjacent Network", "Physical"]
                    elif dataset=="AC":
                        key_list = ["Not High", "High"]
                    elif dataset=="PR":
                        key_list = ["Not High", "High"]
                    elif dataset=="UI":
                        key_list = ["Not Required", "Required"]
                    ground_truth = key_list[int(nshot_data[nshot_id]['ground_truth'])]
                    prompt_item.append({'role':'user', 'content': nshot_clonze})
                    prompt_item.append({'role':'assistant', 'content': 'Category: '+ground_truth})
                    if tokens.num_tokens_from_messages(prompt_item)>7500:
                        print(len(prompt_item)/2)
                        break
                clonze = ''
                prompt_user_2_content = prompt[-1]['content'].format(clonze)
                prompt_item.append({'role':'user', 'content':prompt_user_2_content})
                id = 'summary'
                ground_truth = ''
                prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
                break
            else:
                clonze = '\n'.join(['Function: '+data[id]['function'], 
                                    'Function description: '+data[id]['description']])
        
        elif dataset=='vulfix_extractfix':
            if method=='info-manual':
                clonze = data[id]['info-manual']
            else:
                clonze = data[id]['base']

        if dataset=='vulfix_extractfix' or method=='summary':
            ground_truth = ''
        else:
            ground_truth = data[id]['ground_truth']
        prompt_user_2_content = prompt[-1]['content'].format(clonze)
        prompt_user_2 = {'role':'user', 'content':prompt_user_2_content}        
        if tokens.num_tokens_from_messages([prompt_user_2])>max_tokens:
            print('message processing ({} tokens): {}'.format(max_tokens, id))
            prompt_user_2 = tokens.message_process(prompt_user_2, max_tokens)
        prompt_item.append(prompt_user_2)

        prompts.append({'id':id, 'prompt':prompt_item, 'ground_truth': ground_truth})
        prompt_item_num += 1

    print(len(prompts))
    return prompts