#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# github_merge_tester_v2.py - Teste de merge sem conflitos + resolução automática
#

import os
import sys
import requests
import json
import subprocess
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm

class GitHubMergeTesterV2:
    """Script de teste v2 - foca em merge sem conflitos e resolução automática"""
    
    def __init__(self):
        self.console = Console()
        self.token = None
        self.repo_name = None
        self.headers = None
        
    def get_github_token(self):
        """Obtém o token do GitHub"""
        token_file = os.path.expanduser("~/.GITHUB_TOKEN")
        
        if not os.path.exists(token_file):
            self.console.print("[red]❌ Arquivo de token não encontrado[/]")
            return False
            
        try:
            with open(token_file, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if '=' in line:
                    org, token = line.split('=', 1)
                    self.token = token
                    break
                elif line and '=' not in line:
                    self.token = line
                    break
                    
            if self.token:
                self.headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "GitHubMergeTesterV2/1.0"
                }
                return True
            else:
                return False
                
        except Exception as e:
            self.console.print(f"[red]❌ Erro lendo token: {e}[/]")
            return False
    
    def get_repo_name(self):
        """Obtém o nome do repositório"""
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                stdout=subprocess.PIPE,
                text=True,
                check=True
            )
            
            url = result.stdout.strip()
            import re
            match = re.search(r'[:/]([^/]+/[^.]+)(?:\.git)?$', url)
            if match:
                self.repo_name = match.group(1)
                return True
            return False
                
        except Exception as e:
            return False
    
    def create_clean_test_branch(self):
        """Cria uma branch limpa baseada em main para testar merge sem conflitos"""
        self.console.print("\n[cyan]🌿 Criando branch de teste sem conflitos...[/]")
        
        timestamp = datetime.now().strftime("%H%M%S")
        test_branch = f"test-merge-clean-{timestamp}"
        
        try:
            # Mudar para main
            subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)
            
            # Pull latest main
            subprocess.run(["git", "pull", "origin", "main"], check=True, capture_output=True)
            
            # Criar nova branch baseada em main atualizado
            subprocess.run(["git", "checkout", "-b", test_branch], check=True, capture_output=True)
            
            # Fazer uma pequena mudança para diferenciar
            test_file = "test_merge_file.txt"
            with open(test_file, 'w') as f:
                f.write(f"Arquivo de teste criado em {datetime.now()}\n")
                f.write("Este arquivo será usado para testar merge automático\n")
            
            # Commit da mudança
            subprocess.run(["git", "add", test_file], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Teste: arquivo para merge automático - {timestamp}"], 
                         check=True, capture_output=True)
            
            # Push da branch
            subprocess.run(["git", "push", "origin", test_branch], check=True, capture_output=True)
            
            self.console.print(f"[green]✅ Branch criada: {test_branch}[/]")
            return test_branch
            
        except Exception as e:
            self.console.print(f"[red]❌ Erro criando branch: {e}[/]")
            return None
    
    def create_test_pr_clean(self, source_branch):
        """Cria um PR que deveria ser mergeável sem conflitos"""
        self.console.print(f"\n[cyan]📝 Criando PR sem conflitos: {source_branch} → main[/]")
        
        pr_data = {
            "title": f"[TESTE LIMPO] Auto-merge {source_branch}",
            "body": "PR de teste para verificar auto-merge sem conflitos. Pode ser mesclado automaticamente.",
            "head": source_branch,
            "base": "main"
        }
        
        try:
            response = requests.post(
                f"https://api.github.com/repos/{self.repo_name}/pulls",
                json=pr_data,
                headers=self.headers
            )
            
            if response.status_code in [200, 201]:
                pr_info = response.json()
                pr_number = pr_info.get('number')
                
                self.console.print(f"[green]✅ PR criado: #{pr_number}[/]")
                
                # Aguardar um pouco para GitHub processar
                import time
                time.sleep(2)
                
                return pr_number, pr_info
            else:
                self.console.print(f"[red]❌ Falha criando PR: {response.status_code}[/]")
                return None, None
                
        except Exception as e:
            self.console.print(f"[red]❌ Erro: {e}[/]")
            return None, None
    
    def check_pr_mergeable_status(self, pr_number):
        """Verifica status detalhado do PR e aguarda se necessário"""
        self.console.print(f"\n[cyan]🔍 Verificando status do PR #{pr_number}...[/]")
        
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"https://api.github.com/repos/{self.repo_name}/pulls/{pr_number}", 
                                      headers=self.headers)
                
                if response.status_code == 200:
                    pr_data = response.json()
                    
                    mergeable = pr_data.get('mergeable')
                    mergeable_state = pr_data.get('mergeable_state')
                    
                    self.console.print(f"   Tentativa {attempt + 1}/{max_attempts}:")
                    self.console.print(f"   - Mergeable: {mergeable}")
                    self.console.print(f"   - State: {mergeable_state}")
                    
                    if mergeable is True and mergeable_state == 'clean':
                        self.console.print("[green]   ✅ PR pronto para merge automático![/]")
                        return True, pr_data
                    elif mergeable is False and mergeable_state == 'dirty':
                        self.console.print("[red]   ❌ PR tem conflitos[/]")
                        return False, pr_data
                    elif mergeable_state == 'unknown':
                        self.console.print("[yellow]   ⏳ GitHub ainda processando... aguardando[/]")
                        if attempt < max_attempts - 1:
                            import time
                            time.sleep(3)
                            continue
                    else:
                        self.console.print(f"[yellow]   ⚠️  Estado: {mergeable_state}[/]")
                        return False, pr_data
                        
                return False, None
                
            except Exception as e:
                self.console.print(f"[red]   ❌ Erro verificando PR: {e}[/]")
                return False, None
        
        self.console.print("[red]❌ Timeout verificando status do PR[/]")
        return False, None
    
    def test_auto_merge_clean(self, pr_number):
        """Testa auto-merge em PR sem conflitos"""
        self.console.print(f"\n[cyan]🚀 Testando auto-merge no PR #{pr_number}...[/]")
        
        # Método que deve funcionar: dados completos
        merge_data = {
            "commit_title": f"Auto-merge PR #{pr_number} via teste",
            "commit_message": "Merge automático realizado pelo script de teste",
            "merge_method": "merge"
        }
        
        try:
            merge_url = f"https://api.github.com/repos/{self.repo_name}/pulls/{pr_number}/merge"
            response = requests.put(merge_url, json=merge_data, headers=self.headers)
            
            self.console.print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                merge_info = response.json()
                self.console.print("[green]   🎉 AUTO-MERGE FUNCIONOU![/]")
                self.console.print(f"   - SHA: {merge_info.get('sha', 'N/A')}")
                self.console.print(f"   - Message: {merge_info.get('message', 'N/A')}")
                return True
            else:
                response_data = response.json() if response.text else {}
                self.console.print(f"[red]   ❌ Falha: {response_data.get('message', 'Erro desconhecido')}[/]")
                self.console.print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            self.console.print(f"[red]   ❌ Erro: {e}[/]")
            return False
    
    def cleanup_test_branch(self, branch_name):
        """Remove branch de teste"""
        self.console.print(f"\n[cyan]🧹 Limpando branch de teste: {branch_name}[/]")
        
        try:
            # Voltar para main
            subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)
            
            # Deletar branch local
            subprocess.run(["git", "branch", "-D", branch_name], check=True, capture_output=True)
            
            # Deletar branch remota
            subprocess.run(["git", "push", "origin", "--delete", branch_name], check=True, capture_output=True)
            
            # Remover arquivo de teste se existir
            test_file = "test_merge_file.txt"
            if os.path.exists(test_file):
                os.remove(test_file)
            
            self.console.print("[green]✅ Limpeza concluída[/]")
            
        except Exception as e:
            self.console.print(f"[yellow]⚠️  Erro na limpeza: {e}[/]")
    
    def test_conflict_resolution_strategy(self):
        """Testa estratégias para resolver conflitos automaticamente"""
        self.console.print("\n[cyan]🔧 Testando estratégias de resolução de conflitos...[/]")
        
        # Buscar branches com conflitos
        try:
            response = requests.get(f"https://api.github.com/repos/{self.repo_name}/pulls?state=open", 
                                  headers=self.headers)
            
            if response.status_code == 200:
                open_prs = response.json()
                conflicted_prs = []
                
                for pr in open_prs:
                    pr_detail = requests.get(f"https://api.github.com/repos/{self.repo_name}/pulls/{pr['number']}", 
                                           headers=self.headers)
                    if pr_detail.status_code == 200:
                        pr_data = pr_detail.json()
                        if pr_data.get('mergeable_state') == 'dirty':
                            conflicted_prs.append(pr_data)
                
                if conflicted_prs:
                    self.console.print(f"[yellow]📋 Encontrados {len(conflicted_prs)} PRs com conflitos[/]")
                    
                    # Testar estratégia: force update da branch
                    pr = conflicted_prs[0]
                    self.console.print(f"\n   🎯 Testando resolução no PR #{pr['number']}")
                    self.console.print(f"   - Head branch: {pr['head']['ref']}")
                    self.console.print(f"   - Base branch: {pr['base']['ref']}")
                    
                    # Simular estratégia que será implementada no código principal
                    self.console.print("\n   📝 Estratégias possíveis:")
                    self.console.print("   1. Update da branch dev-* com main antes do merge")
                    self.console.print("   2. Merge com estratégia 'ours' ou 'theirs'")
                    self.console.print("   3. Rebase automático da branch dev-*")
                    
                else:
                    self.console.print("[green]✅ Nenhum PR com conflitos encontrado no momento[/]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Erro: {e}[/]")
    
    def run_full_test(self):
        """Executa teste completo v2"""
        self.console.print("[bold blue]🚀 TESTE V2 - MERGE SEM CONFLITOS + ESTRATÉGIAS[/]")
        
        # Setup básico
        if not self.get_github_token():
            return
        if not self.get_repo_name():
            return
        
        self.console.print(f"[green]✅ Repositório: {self.repo_name}[/]")
        
        # Pergunta se quer continuar
        if not Confirm.ask("\n[yellow]Este teste criará branches e PRs temporários. Continuar?[/]"):
            self.console.print("[yellow]Teste cancelado pelo usuário[/]")
            return
        
        # Teste 1: Merge sem conflitos
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]TESTE 1: MERGE SEM CONFLITOS[/]")
        
        test_branch = self.create_clean_test_branch()
        if not test_branch:
            return
        
        pr_number, pr_info = self.create_test_pr_clean(test_branch)
        if not pr_number:
            self.cleanup_test_branch(test_branch)
            return
        
        is_mergeable, pr_data = self.check_pr_mergeable_status(pr_number)
        
        if is_mergeable:
            merge_success = self.test_auto_merge_clean(pr_number)
            
            if merge_success:
                self.console.print("\n[bold green]🎉 RESULTADO: AUTO-MERGE FUNCIONA PERFEITAMENTE![/]")
                self.console.print("[green]✅ O problema está nos CONFLITOS, não no código de merge[/]")
            else:
                self.console.print("\n[bold red]❌ RESULTADO: Problema no método de merge[/]")
        else:
            self.console.print("\n[bold yellow]⚠️  RESULTADO: Branch de teste tem conflitos inesperados[/]")
        
        # Limpeza só se não foi mesclado
        if not merge_success:
            self.cleanup_test_branch(test_branch)
        
        # Teste 2: Estratégias para conflitos
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]TESTE 2: ANÁLISE DE CONFLITOS[/]")
        self.test_conflict_resolution_strategy()
        
        # Relatório final
        self.console.print("\n" + "="*60)
        self.console.print("[bold blue]📋 CONCLUSÕES:[/]")
        self.console.print("1. Se auto-merge funcionou sem conflitos → problema está na resolução de conflitos")
        self.console.print("2. Se auto-merge falhou mesmo sem conflitos → problema no método de merge")
        self.console.print("3. Próximo passo: implementar resolução automática de conflitos no código principal")

def main():
    tester = GitHubMergeTesterV2()
    tester.run_full_test()

if __name__ == "__main__":
    main()