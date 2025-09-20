"""
機器管理模組 - 負責機器分配和管理
"""

from typing import Dict, List, Optional
from app.utils import load_config
from dataclasses import dataclass

@dataclass
class Machine:
    ip: str
    vendor: str
    model: str
    ticket_id: Optional[str] = None

class MachineManager:
    """機器管理器 - 負責機器分配、釋放和狀態管理"""
    
    def __init__(self):
        """
        初始化機器管理器
        """
        self._machines: Dict[str, Machine] = self._load_machines_from_config()
        
    def _load_machines_from_config(self) -> Dict[str, Machine]:
        config = load_config()
        machines: Dict[str, Machine] = {}
        for vendor, models in config.items():
            for model, details in models.items():
                ips = details.get("ips", [])
                for ip in ips:
                    machines[ip] = Machine(ip=ip, vendor=vendor, model=model)
        return machines
        
        
    def _get_available_machines(self, vendor: str, model: str) -> List[Machine]:
        """取得空閒的機器列表"""
        available = []
        for machine in self._machines.values():
            if machine.ticket_id is None and machine.vendor == vendor and machine.model == model:
                available.append(machine)
        return available

    def allocate_machine(self, ticket_id: str, vendor: str, model: str) -> Optional[str]:
        """
        為票據分配機器
        
        Args:
            ticket_id: 票據ID
            
        Returns:
            Optional[str]: 分配的機器ID，如果無可用機器則返回 None
        """
        available_machines = self._get_available_machines(vendor, model)
        if not available_machines:
            print(f"[MachineManager] No available machines for ticket: {ticket_id}")
            return None
        
        # 使用第一個可用機器策略
        selected_machine = available_machines[0]
        
        if not selected_machine:
            print(f"[MachineManager] Failed to select machine for ticket: {ticket_id}")
            return None
        
        # 分配機器
        self._machines[selected_machine.ip].ticket_id = ticket_id
        print(f"[MachineManager] Allocated machine: {selected_machine.ip} to ticket: {ticket_id}")
        return selected_machine.ip
    
    def release_machine(self, machine_ip: str) -> bool:
        """
        釋放機器
        
        Args:
            machine_ip: 機器ID
            
        Returns:
            bool: 是否成功釋放
        """
        if machine_ip not in self._machines:
            print(f"[MachineManager] Machine {machine_ip} not found")
            return False

        ticket_id = self._machines[machine_ip].ticket_id
        self._machines[machine_ip].ticket_id = None
        print(f"[MachineManager] Released machine: {machine_ip} (was processing ticket: {ticket_id})")
        return True
    
    def validate_ticket_machine(self, ticket_id: str, machine_ip: str) -> bool:
        """
        驗證票據確實分配給指定機器
        
        Args:
            ticket_id: 票據ID
            machine_ip: 機器ID
            
        Returns:
            bool: 是否匹配
        """
        machine = self._machines.get(machine_ip)
        machine_ticket = machine.ticket_id if machine else None

        return machine_ticket == ticket_id

    def get_machine_status(self) -> Dict[str, Optional[str]]:
        """
        取得所有機器的狀態
        
        Returns:
            Dict[str, Optional[str]]: 機器狀態 (None = 空閒, 票據ID = 忙碌)
        """
        return {ip: machine.ticket_id for ip, machine in self._machines.items()}
    
    def get_running_count(self) -> int:
        """
        取得正在執行中的票據數量
        
        Returns:
            int: 執行中的票據數量
        """
        count = 0
        for machine in self._machines.values():
            if machine.ticket_id is not None:
                count += 1
        return count