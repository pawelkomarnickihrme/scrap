#!/usr/bin/env python3
"""
Moduł do zarządzania połączeniem OpenVPN.
Uruchamia i zarządza połączeniem VPN przed scrapowaniem.
"""

import asyncio
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class VPNManager:
    """Zarządza połączeniem OpenVPN."""
    
    def __init__(self, ovpn_dir: str = "ovpn_tcp", username: str = None, password: str = None, sudo_password: str = None):
        """
        Inicjalizuje VPNManager.
        
        Args:
            ovpn_dir: Katalog z plikami .ovpn
            username: Login do VPN
            password: Hasło do VPN
            sudo_password: Hasło sudo (jeśli None, spróbuje bez sudo)
        """
        self.ovpn_dir = Path(ovpn_dir)
        self.username = username or "a24P6VnUBmjzqMf1Bcf1LUch"
        self.password = password or "LYJNY9sfseGHVey6VXUEQ2Nk"
        self.sudo_password = sudo_password
        self.current_ovpn_file: Optional[Path] = None
        self.vpn_process: Optional[subprocess.Popen] = None
        self.connected = False
        
    def get_ovpn_files(self) -> list:
        """Zwraca listę wszystkich plików .ovpn w katalogu."""
        if not self.ovpn_dir.exists():
            raise FileNotFoundError(f"Katalog {self.ovpn_dir} nie istnieje")
        
        ovpn_files = list(self.ovpn_dir.glob("*.ovpn"))
        return sorted(ovpn_files)
    
    def select_random_ovpn(self) -> Path:
        """Wybiera losowy plik .ovpn."""
        ovpn_files = self.get_ovpn_files()
        if not ovpn_files:
            raise FileNotFoundError(f"Brak plików .ovpn w katalogu {self.ovpn_dir}")
        
        return random.choice(ovpn_files)
    
    def select_next_ovpn(self, current_file: Optional[Path] = None) -> Path:
        """Wybiera następny plik .ovpn (kolejny po aktualnym lub losowy)."""
        ovpn_files = self.get_ovpn_files()
        if not ovpn_files:
            raise FileNotFoundError(f"Brak plików .ovpn w katalogu {self.ovpn_dir}")
        
        if current_file and current_file in ovpn_files:
            try:
                current_index = ovpn_files.index(current_file)
                next_index = (current_index + 1) % len(ovpn_files)
                return ovpn_files[next_index]
            except ValueError:
                pass
        
        return random.choice(ovpn_files)
    
    def _check_vpn_interface(self) -> bool:
        """Sprawdza czy interfejs VPN jest aktywny (działa na macOS i Linux)."""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            # Sprawdź wszystkie możliwe interfejsy utun (utun0, utun1, itd.)
            for i in range(10):  # Sprawdź utun0-utun9
                try:
                    result = subprocess.run(
                        ["ifconfig", f"utun{i}"],
                        capture_output=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        # Sprawdź czy ma adres IP
                        output = result.stdout.decode()
                        if "inet " in output:
                            return True
                except:
                    pass
            return False
        else:  # Linux
            try:
                result = subprocess.run(
                    ["ip", "link", "show", "tun0"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    # Sprawdź IP
                    ip_result = subprocess.run(
                        ["ip", "addr", "show", "tun0"],
                        capture_output=True,
                        timeout=2
                    )
                    return "inet " in ip_result.stdout.decode()
            except:
                pass
        
        return False
    
    def create_auth_file(self) -> Path:
        """Tworzy tymczasowy plik z danymi logowania."""
        auth_file = Path("/tmp/openvpn_auth.txt")
        with open(auth_file, "w") as f:
            f.write(f"{self.username}\n{self.password}\n")
        os.chmod(auth_file, 0o600)  # Ustaw uprawnienia tylko dla właściciela
        return auth_file
    
    def _read_openvpn_log(self) -> str:
        """Czyta logi OpenVPN."""
        log_file = Path("/tmp/openvpn-scraper.log")
        if log_file.exists():
            try:
                return log_file.read_text(encoding="utf-8", errors="ignore")
            except:
                return ""
        return ""
    
    def _check_openvpn_process(self) -> bool:
        """Sprawdza czy proces OpenVPN działa (sprawdza PID plik)."""
        pid_file = Path("/tmp/openvpn-scraper.pid")
        if not pid_file.exists():
            return False
        
        try:
            pid = int(pid_file.read_text().strip())
            # Sprawdź czy proces z tym PID istnieje
            result = subprocess.run(
                ["ps", "-p", str(pid)],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    async def connect(self, ovpn_file: Optional[Path] = None, max_wait: int = 60) -> bool:
        """
        Uruchamia połączenie VPN.
        
        Args:
            ovpn_file: Plik .ovpn do użycia (jeśli None, wybierze losowy)
            max_wait: Maksymalny czas oczekiwania na połączenie (sekundy, domyślnie 60)
        
        Returns:
            True jeśli połączenie się powiodło, False w przeciwnym razie
        """
        # Sprawdź rzeczywisty stan interfejsu VPN, nie tylko flagę
        if self._check_vpn_interface():
            if self.current_ovpn_file:
                print(f"⚠️  VPN już jest połączony (konfiguracja: {self.current_ovpn_file.name})")
            else:
                print("⚠️  VPN już jest połączony (nieznana konfiguracja)")
            self.connected = True
            return True
        
        if ovpn_file is None:
            ovpn_file = self.select_random_ovpn()
        
        self.current_ovpn_file = ovpn_file
        auth_file = self.create_auth_file()
        
        print(f"🔌 Łączenie z VPN: {ovpn_file.name}")
        
        # Sprawdź czy openvpn jest dostępny
        try:
            subprocess.run(["which", "openvpn"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("❌ Błąd: OpenVPN nie jest zainstalowany lub nie jest w PATH", file=sys.stderr)
            return False
        
        # Usuń stare logi i PID jeśli istnieją
        log_file = Path("/tmp/openvpn-scraper.log")
        pid_file = Path("/tmp/openvpn-scraper.pid")
        try:
            if log_file.exists():
                log_file.unlink()
            if pid_file.exists():
                pid_file.unlink()
        except:
            pass
        
        # Uruchom OpenVPN w tle z sudo jeśli wymagane
        base_cmd = [
            "openvpn",
            "--config", str(ovpn_file),
            "--auth-user-pass", str(auth_file),
            "--daemon", "openvpn-scraper",
            "--writepid", "/tmp/openvpn-scraper.pid",
            "--log", "/tmp/openvpn-scraper.log",
            "--verb", "3"
        ]
        
        # Jeśli mamy hasło sudo, użyj sudo -S (czyta hasło ze stdin)
        if self.sudo_password:
            cmd = ["sudo", "-S"] + base_cmd
            print("🔐 Używanie sudo do uruchomienia OpenVPN...")
        else:
            cmd = base_cmd
            print("⚠️  Uruchamianie OpenVPN bez sudo (może wymagać uprawnień)")
        
        try:
            # Uruchom proces
            if self.sudo_password:
                # Przekaż hasło sudo przez stdin
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                # Wyślij hasło sudo
                if process.stdin:
                    process.stdin.write(f"{self.sudo_password}\n".encode())
                    await process.stdin.drain()
                    process.stdin.close()
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # Poczekaj chwilę na uruchomienie
            await asyncio.sleep(0.1)
            
            # Sprawdź czy proces nadal działa
            if process.returncode is not None and process.returncode != 0:
                stdout, stderr = await process.communicate()
                error_msg = stderr.decode() if stderr else "Brak szczegółów błędu"
                print(f"❌ Błąd uruchamiania OpenVPN: {error_msg}", file=sys.stderr)
                # Sprawdź logi
                log_content = self._read_openvpn_log()
                if log_content:
                    print(f"📋 Logi OpenVPN:\n{log_content[-500:]}", file=sys.stderr)  # Ostatnie 500 znaków
                return False
            
            # Sprawdź czy proces OpenVPN rzeczywiście się uruchomił
            if not self._check_openvpn_process():
                log_content = self._read_openvpn_log()
                if log_content:
                    print(f"⚠️  OpenVPN nie uruchomił się poprawnie. Logi:\n{log_content[-500:]}", file=sys.stderr)
                else:
                    print("⚠️  OpenVPN nie uruchomił się poprawnie (brak logów)", file=sys.stderr)
                return False
            
            # Czekaj na połączenie (sprawdzaj interfejs tun)
            start_time = time.time()
            check_interval = 0.1  # Sprawdzaj co 0.1 sekundy - maksymalna prędkość
            last_log_check = 0
            
            while time.time() - start_time < max_wait:
                elapsed = time.time() - start_time
                
                # Sprawdź interfejs VPN
                if self._check_vpn_interface():
                    self.connected = True
                    print(f"✓ Połączono z VPN: {ovpn_file.name} (po {elapsed:.1f}s)")
                    print(f"📋 Aktywna konfiguracja: {ovpn_file.name}")
                    return True
                
                # Co 1 sekundę sprawdź logi, aby zobaczyć postęp
                if elapsed - last_log_check >= 1:
                    log_content = self._read_openvpn_log()
                    if log_content:
                        # Szukaj błędów w logach
                        if "ERROR" in log_content or "FATAL" in log_content:
                            error_lines = [line for line in log_content.split("\n") if "ERROR" in line or "FATAL" in line]
                            if error_lines:
                                print(f"⚠️  Błędy w logach OpenVPN: {error_lines[-3:]}", file=sys.stderr)
                    last_log_check = elapsed
                
               
            
            # Timeout - sprawdź logi, aby zobaczyć co poszło nie tak
            log_content = self._read_openvpn_log()
            print(f"⚠️  Timeout podczas łączenia z VPN (oczekiwano {max_wait}s)", file=sys.stderr)
            if log_content:
                # Pokaż ostatnie linie logów
                log_lines = log_content.split("\n")
                print(f"📋 Ostatnie linie logów OpenVPN:", file=sys.stderr)
                for line in log_lines[-10:]:
                    if line.strip():
                        print(f"   {line}", file=sys.stderr)
            else:
                print("   Brak logów OpenVPN", file=sys.stderr)
            
            return False
            
        except Exception as e:
            print(f"❌ Błąd podczas łączenia z VPN: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            # Sprawdź logi w przypadku wyjątku
            log_content = self._read_openvpn_log()
            if log_content:
                print(f"📋 Logi OpenVPN:\n{log_content[-500:]}", file=sys.stderr)
            return False
        finally:
            # Usuń plik auth po użyciu (opcjonalnie)
            try:
                auth_file.unlink()
            except:
                pass
    
    async def disconnect(self):
        """Rozłącza VPN."""
        print("🔌 Rozłączanie VPN...")
        
        try:
            # Najpierw spróbuj użyć PID z pliku PID (najbardziej niezawodna metoda)
            pid_file = Path("/tmp/openvpn-scraper.pid")
            pid_killed = False
            
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    # Sprawdź czy proces z tym PID istnieje
                    check_process = subprocess.run(
                        ["ps", "-p", str(pid)],
                        capture_output=True,
                        timeout=2
                    )
                    
                    if check_process.returncode == 0:
                        # Proces istnieje, zabij go
                        kill_cmd = ["kill", "-TERM", str(pid)]
                        if self.sudo_password:
                            kill_cmd = ["sudo", "-S"] + kill_cmd
                        
                        kill_process = await asyncio.create_subprocess_exec(
                            *kill_cmd,
                            stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        if self.sudo_password and kill_process.stdin:
                            kill_process.stdin.write(f"{self.sudo_password}\n".encode())
                            await kill_process.stdin.drain()
                            kill_process.stdin.close()
                        
                        await kill_process.wait()
                        pid_killed = True
                        print(f"✓ Wysłano sygnał TERM do procesu OpenVPN (PID: {pid})")
                        
                        # Poczekaj chwilę na zamknięcie
                        await asyncio.sleep(0.5)
                        
                        # Jeśli proces nadal istnieje, użyj SIGKILL
                        check_again = subprocess.run(
                            ["ps", "-p", str(pid)],
                            capture_output=True,
                            timeout=2
                        )
                        
                        if check_again.returncode == 0:
                            kill_force_cmd = ["kill", "-9", str(pid)]
                            if self.sudo_password:
                                kill_force_cmd = ["sudo", "-S"] + kill_force_cmd
                            
                            kill_force = await asyncio.create_subprocess_exec(
                                *kill_force_cmd,
                                stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            
                            if self.sudo_password and kill_force.stdin:
                                kill_force.stdin.write(f"{self.sudo_password}\n".encode())
                                await kill_force.stdin.drain()
                                kill_force.stdin.close()
                            
                            await kill_force.wait()
                            print(f"✓ Wymuszono zamknięcie procesu OpenVPN (PID: {pid})")
                except (ValueError, subprocess.TimeoutExpired, Exception) as e:
                    # Jeśli nie udało się użyć PID, przejdź do killall
                    pass
            
            # Jeśli nie udało się użyć PID lub PID nie istnieje, użyj killall
            if not pid_killed:
                # Znajdź wszystkie procesy OpenVPN związane z naszym daemonem
                # Najpierw spróbuj pkill (bardziej niezawodne na macOS)
                pkill_cmd = ["pkill", "-f", "openvpn-scraper"]
                if self.sudo_password:
                    pkill_cmd = ["sudo", "-S"] + pkill_cmd
                
                try:
                    pkill_process = await asyncio.create_subprocess_exec(
                        *pkill_cmd,
                        stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    if self.sudo_password and pkill_process.stdin:
                        pkill_process.stdin.write(f"{self.sudo_password}\n".encode())
                        await pkill_process.stdin.drain()
                        pkill_process.stdin.close()
                    
                    await pkill_process.wait()
                    print("✓ Użyto pkill do zakończenia procesów OpenVPN")
                    await asyncio.sleep(0.5)
                except:
                    pass
                
                # Jako fallback użyj killall
                killall_cmd = ["killall", "openvpn"]
                if self.sudo_password:
                    killall_cmd = ["sudo", "-S"] + killall_cmd
                
                killall_process = await asyncio.create_subprocess_exec(
                    *killall_cmd,
                    stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                if self.sudo_password and killall_process.stdin:
                    killall_process.stdin.write(f"{self.sudo_password}\n".encode())
                    await killall_process.stdin.drain()
                    killall_process.stdin.close()
                
                returncode = await killall_process.wait()
                
                if returncode == 0:
                    print("✓ Procesy OpenVPN zakończone przez killall")
                elif returncode == 1:
                    print("ℹ️  Nie znaleziono aktywnych procesów OpenVPN")
            
            # Usuń plik PID jeśli istnieje
            try:
                if pid_file.exists():
                    pid_file.unlink()
            except:
                pass
            
            # Poczekaj chwilę na zamknięcie interfejsu
            await asyncio.sleep(1.0)
            
            # Sprawdź czy rzeczywiście się rozłączyło
            if not self._check_vpn_interface():
                self.connected = False
                config_name = self.get_current_config()
                if config_name:
                    print(f"✓ VPN rozłączony (konfiguracja: {config_name})")
                else:
                    print("✓ VPN rozłączony")
                self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
            else:
                print("⚠️  VPN nadal wydaje się być połączony - próba wymuszonego rozłączenia...")
                # Ostatnia próba - użyj killall -9
                try:
                    killall_force_cmd = ["killall", "-9", "openvpn"]
                    if self.sudo_password:
                        killall_force_cmd = ["sudo", "-S"] + killall_force_cmd
                    
                    killall_force = await asyncio.create_subprocess_exec(
                        *killall_force_cmd,
                        stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    if self.sudo_password and killall_force.stdin:
                        killall_force.stdin.write(f"{self.sudo_password}\n".encode())
                        await killall_force.stdin.drain()
                        killall_force.stdin.close()
                    
                    await killall_force.wait()
                    await asyncio.sleep(1.0)
                    
                    # Sprawdź ponownie
                    if not self._check_vpn_interface():
                        self.connected = False
                        config_name = self.get_current_config()
                        if config_name:
                            print(f"✓ VPN rozłączony (wymuszone, konfiguracja: {config_name})")
                        else:
                            print("✓ VPN rozłączony (wymuszone)")
                        self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
                    else:
                        self.connected = False  # Ustaw flagę mimo wszystko
                        self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
                        print("⚠️  Nie udało się potwierdzić rozłączenia, ale procesy zostały zakończone")
                except Exception as e:
                    print(f"⚠️  Błąd podczas wymuszonego rozłączenia: {e}", file=sys.stderr)
                    self.connected = False  # Ustaw flagę mimo wszystko
                    self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
            
        except PermissionError as e:
            print(f"⚠️  Błąd uprawnień podczas rozłączania VPN: {e}", file=sys.stderr)
            print("💡 Wskazówka: Upewnij się, że masz uprawnienia sudo lub użyj 'sudo killall openvpn' ręcznie", file=sys.stderr)
            self.connected = False
            self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
        except Exception as e:
            print(f"⚠️  Błąd podczas rozłączania VPN: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            # Spróbuj jeszcze raz jako fallback
            try:
                killall_cmd = ["killall", "-9", "openvpn"]
                if self.sudo_password:
                    killall_cmd = ["sudo", "-S"] + killall_cmd
                
                killall_process = await asyncio.create_subprocess_exec(
                    *killall_cmd,
                    stdin=asyncio.subprocess.PIPE if self.sudo_password else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                if self.sudo_password and killall_process.stdin:
                    killall_process.stdin.write(f"{self.sudo_password}\n".encode())
                    await killall_process.stdin.drain()
                    killall_process.stdin.close()
                
                await killall_process.wait()
                await asyncio.sleep(1.0)
                self.connected = False
                self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
            except:
                self.connected = False
                self.current_ovpn_file = None  # Wyczyść aktualną konfigurację
    
    async def reconnect_with_new_config(self) -> bool:
        """Rozłącza obecne połączenie i łączy z nową konfiguracją."""
        current_config = self.get_current_config()
        if current_config:
            print(f"🔄 Zmienianie konfiguracji VPN (obecna: {current_config})...")
        else:
            print("🔄 Zmienianie konfiguracji VPN...")
        
        # Sprawdź czy VPN jest rzeczywiście połączony przed próbą rozłączenia
        if self._check_vpn_interface():
            await self.disconnect()
            # Poczekaj dłużej na pełne rozłączenie przed próbą ponownego połączenia
            await asyncio.sleep(2.0)
        else:
            # Jeśli nie jest połączony, po prostu zaktualizuj flagę
            self.connected = False
        
        if self.current_ovpn_file:
            next_file = self.select_next_ovpn(self.current_ovpn_file)
        else:
            next_file = self.select_random_ovpn()
        
        result = await self.connect(next_file)
        if result:
            print(f"📋 Nowa aktywna konfiguracja: {next_file.name}")
        return result
    
    def get_current_config(self) -> Optional[str]:
        """Zwraca nazwę aktualnie wczytanej konfiguracji VPN."""
        if self.current_ovpn_file:
            return self.current_ovpn_file.name
        return None
    
    def is_connected(self) -> bool:
        """Sprawdza czy VPN jest połączony."""
        if not self.connected:
            return False
        
        # Sprawdź rzeczywisty stan interfejsu
        return self._check_vpn_interface()
    
    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.disconnect()

