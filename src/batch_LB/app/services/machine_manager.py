"""
機器管理模組 - 負責機器分配和管理
"""

from typing import Dict, List, Optional
import itertools


class MachineManager:
    """機器管理器 - 負責機器分配、釋放和狀態管理"""
    
    DEFAULT_MACHINES = ["machine_1", "machine_2", "machine_3"]
    
    def __init__(self, strategy_type: str = "first_available", machine_ids: Optional[List[str]] = None):
        """
        初始化機器管理器
        
        Args:
            strategy_type: 策略類型 ("first_available" 或 "round_robin")
            machine_ids: 機器ID列表，如果為None則使用預設配置
        """
        if machine_ids is None:
            machine_ids = self.DEFAULT_MACHINES
            
        self._machines: Dict[str, Optional[str]] = {
            machine_id: None for machine_id in machine_ids
        }
        
        self._strategy_type = strategy_type
        if strategy_type == "round_robin":
            self._round_robin_iterator = itertools.cycle(machine_ids)
        
        print(f"[MachineManager] Initialized with machines: {machine_ids}")
        print(f"[MachineManager] Using strategy: {strategy_type}")
    
    def _get_available_machines(self) -> List[str]:
        """取得空閒的機器列表"""
        return [machine_id for machine_id, ticket_id in self._machines.items() if ticket_id is None]
    
    def _select_machine_first_available(self, available_machines: List[str]) -> Optional[str]:
        """第一個可用機器策略"""
        return available_machines[0] if available_machines else None
    
    def _select_machine_round_robin(self, available_machines: List[str]) -> Optional[str]:
        """Round Robin 機器分配策略"""
        if not available_machines:
            return None
        
        if len(available_machines) == 1:
            return available_machines[0]
        
        # Round Robin 邏輯：尋找下一台可用的機器
        attempts = 0
        while attempts < len(self._machines):
            next_machine = next(self._round_robin_iterator)
            if next_machine in available_machines:
                return next_machine
            attempts += 1
        
        # 如果 Round Robin 失敗，回退到第一個可用機器
        return available_machines[0]
    
    def allocate_machine(self, ticket_id: str) -> Optional[str]:
        """
        為票據分配機器
        
        Args:
            ticket_id: 票據ID
            
        Returns:
            Optional[str]: 分配的機器ID，如果無可用機器則返回 None
        """
        available_machines = self._get_available_machines()
        if not available_machines:
            print(f"[MachineManager] No available machines for ticket: {ticket_id}")
            return None
        
        # 根據策略選擇機器
        if self._strategy_type == "round_robin":
            selected_machine = self._select_machine_round_robin(available_machines)
        else:
            selected_machine = self._select_machine_first_available(available_machines)
        
        if not selected_machine:
            print(f"[MachineManager] Strategy failed to select machine for ticket: {ticket_id}")
            return None
        
        # 分配機器
        self._machines[selected_machine] = ticket_id
        print(f"[MachineManager] Allocated machine: {selected_machine} to ticket: {ticket_id}")
        return selected_machine
    
    def release_machine(self, machine_id: str) -> bool:
        """
        釋放機器
        
        Args:
            machine_id: 機器ID
            
        Returns:
            bool: 是否成功釋放
        """
        if machine_id not in self._machines:
            print(f"[MachineManager] Machine {machine_id} not found")
            return False
        
        ticket_id = self._machines[machine_id]
        self._machines[machine_id] = None
        print(f"[MachineManager] Released machine: {machine_id} (was processing ticket: {ticket_id})")
        return True
    
    def validate_ticket_machine(self, ticket_id: str, machine_id: str) -> bool:
        """
        驗證票據確實分配給指定機器
        
        Args:
            ticket_id: 票據ID
            machine_id: 機器ID
            
        Returns:
            bool: 是否匹配
        """
        return self._machines.get(machine_id) == ticket_id
    
    def get_machine_status(self) -> Dict[str, Optional[str]]:
        """
        取得所有機器的狀態
        
        Returns:
            Dict[str, Optional[str]]: 機器狀態 (None = 空閒, 票據ID = 忙碌)
        """
        return self._machines.copy()
    
    def get_running_count(self) -> int:
        """
        取得正在執行中的票據數量
        
        Returns:
            int: 執行中的票據數量
        """
        return sum(1 for ticket_id in self._machines.values() if ticket_id is not None)