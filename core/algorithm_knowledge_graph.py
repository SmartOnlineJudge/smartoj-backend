class AlgorithmKnowledgeGraph:
    def __init__(self):
        # 核心数据结构：前驱依赖字典 (key: 知识点, value: 前置依赖列表)
        self.prerequisites = {
            # Tier 1: 基础基石
            "数组": [],
            "递归": [],
            "数学": [],
            "模拟": [],
            
            # Tier 2: 基础算法与线性结构
            "字符串": ["数组", "模拟"],
            "哈希表": ["数组"],
            "排序": ["数组"],
            "位运算": ["数学"],
            "前缀和": ["数组"],
            "双指针": ["数组"],
            "链表": ["数组"],
            "矩阵": ["数组", "模拟"],
            
            # Tier 3: 中级结构与搜索
            "二分查找": ["排序"],
            "滑动窗口": ["双指针"],
            "栈": ["链表", "数组"],
            "队列": ["链表", "数组"],
            "树": ["递归"],
            "分治": ["递归"],
            "深度优先搜索": ["递归", "栈"],
            "广度优先搜索": ["队列"],
            
            # Tier 4: 高级结构与进阶算法
            "二叉树": ["树"],
            "回溯": ["深度优先搜索"],
            "并查集": ["树"],
            "动态规划": ["递归", "数组"],
            "最短路径": ["广度优先搜索", "深度优先搜索"],
            
            # Tier 5: 专家级/特定领域
            "二叉搜索树": ["二叉树"],
            "堆": ["二叉树"],
            "多维动态规划": ["动态规划", "矩阵"],
            "线段树": ["树", "前缀和"],
            "树状数组": ["前缀和"],
            "最短生成树": ["并查集", "树"]
        }
        
        # 自动生成后继节点字典 (用于查看学完 A 之后可以学什么)
        self.successors = self._generate_successors()

    def _generate_successors(self):
        succ = {tag: [] for tag in self.prerequisites}
        for post_tag, pre_tags in self.prerequisites.items():
            for pre in pre_tags:
                if pre in succ:
                    succ[pre].append(post_tag)
        return succ

    def get_predecessors(self, tag):
        """获取某知识点的直接前驱"""
        return self.prerequisites.get(tag, [])

    def get_successors(self, tag):
        """获取某知识点解锁后的后继"""
        return self.successors.get(tag, [])

    def is_unlocked(self, tag, strong_tags):
        """
        核心逻辑：根据用户掌握的标签判断某个知识点是否解锁
        :param tag: 目标标签
        :param strong_tags: 用户画像中的 strong_tags (set 类型)
        """
        pres = self.get_predecessors(tag)
        if not pres:
            return True
        # 只有当所有前置知识都在 strong_tags 中，才算解锁
        return all(pre in strong_tags for pre in pres)


graph = AlgorithmKnowledgeGraph()
