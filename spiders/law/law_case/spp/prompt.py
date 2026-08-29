prompt = """
{
  "role": "资深法律数据分析专家",
  "task": "从司法案例文本中提取结构化信息,保留完整原始信息",
  "requirements": {
    "output_format": "字典类型",
    "rule": [
        "不要总结、不要改写、不要解释",
        "必须逐字（verbatim）复制原文内容",
        "保留所有标点、空格、换行、全角/半角符号",
        "如果找不到对应内容，返回空字符串",
    ],
    "fields": [
      {"name": "title", "description": "案例名称", "source": "大标题"},
      {"name": "court_name", "description": "审理检察院名称", "source": "全文"},
      {"name": "keyword", "description": "关键词", "source": "二级标题"},
      {"name": "judgment_essence", "description": "要旨/技术要点", "source": "二级标题"},
      {"name": "basic_facts", "description": "基本案情", "source": "二级标题"},
      {"name": "judgment_reason", "description": "履职/诉讼/监督/听证过程", "source": "二级标题"},
      {"name": "judgment_mean", "description": "典型意义", "source": "二级标题"},
      {"name": "related_info", "description": "相关法律规定/相关规定/相关立法", "source": "二级标题"},
    ],
    "processing_steps": [
      "1. 识别案例边界：以标题为分割点区分不同案例",
      "2. 字段提取：根据二级标题分类标记内容（如包含'关键词'的段落存入keyword字段）",
      "3. 数据清洗：去除无关符号/空白字符，保留纯文本内容",
      "4. 格式验证：确保每个案例包含所有必填字段（缺失字段标记为null）",
      "5. 输出构建：将处理后的案例按标准JSON格式组装"
    ],
    "quality_control": {
      "validation_rules": [
        "每个JSON对象必须包含8个预定义字段",
        "字段值必须是字符串或null",
        "最终输出应为字典类型"
      ],
      "example_output": 
        {
          "title": "王某诉某公司劳动争议案",
          "court_name": "上海市徐汇区人民检察院",
          "keyword": "劳动合同解除",
          "judgment_essence": "用人单位单方解除的程序合法性审查",
          "basic_facts": "王某因绩效考核不达标被解除劳动合同...",
          "judgment_reason": "公司未履行培训义务直接解除...",
          "judgment_mean": "明确了用人单位单方解除的正当程序要求...",
          "related_info": "《劳动合同法》第40条"
        }
    }
  }
}
"""