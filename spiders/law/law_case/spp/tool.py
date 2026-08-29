from bs4 import BeautifulSoup


def extract_cases(html_text):
    # 案例分块
    soup = BeautifulSoup(html_text, 'html.parser')
    ps = soup.select('#fontzoom p')

    # 找出所有案号 p 的索引
    case_indices = []
    for i, p in enumerate(ps):
        text = p.get_text(strip=True)
        if text.startswith('（检例第') and '号）' in text:
            case_indices.append(i)

    # 案例数量
    n = len(case_indices)
    modules = []

    if n > 0:
        # 每个案例：标题 + 案号 + 后续内容
        for idx, start_i in enumerate(case_indices):
            title_i = start_i - 1  # 标题在案号前一行
            if idx == n - 1:
                # 最后一个案例：到末尾
                end_i = len(ps)
            else:
                # 下一个案例的标题前一行
                end_i = case_indices[idx + 1] - 1

            case_ps = [ps[title_i]] + ps[start_i:end_i]
            case_title = ps[title_i].get_text(strip=True)
            modules.append((case_title, case_ps))
    else:
        modules.append(('全文', ps))
    return modules


def format_modules(text_list):
    """
    格式化每个【】标题下的内容
    :param text_list: list 解析p标间内的文本
    """
    # ===== 步骤1：创建公用列表 =====
    common_list = []
    tail_idx = None

    # ===== 步骤2：获取所有【】标题行坐标（严格整行匹配）=====
    title_indices = []
    for idx, line in enumerate(text_list):
        if '办案检察院：' in line:
            tail_idx = idx
            break

    if tail_idx is not None:
        # 将最后一个【】不包含的内容，提取到列表最前
        tail_list = text_list[tail_idx:]
        front = text_list[:tail_idx]
        new_text_list = tail_list + front
    else:
        new_text_list = text_list

    for idx, line in enumerate(new_text_list):
        if line.startswith('【'):
            title_indices.append(idx)

    if not title_indices:
        return ""

    # ===== 步骤3：循环处理每个标题区间 =====
    n = len(title_indices)

    for i, start_idx in enumerate(title_indices):
        # 添加第一次前面的所有元素
        if i == 0:
            common_list.extend(new_text_list[:start_idx+1])
        else:
            common_list.append(new_text_list[start_idx])
        # (2) 确定内容结束位置
        end_idx = title_indices[i + 1] if i < n - 1 else len(new_text_list)
        # (3) 拼接内容块：start_idx+1 到 end_idx 之间的所有行
        content_block = new_text_list[start_idx + 1: end_idx]
        # (4) 拼接结果加入公用列表（即使为空也加入空字符串，保持结构）
        common_list.append(' '.join(content_block))

    # ===== 返回最终字符串 =====
    return common_list


def select_content(contents, query_word, return_next=True):
    """
    文本内容查询
    :param contents: list
    :param query_word: str 将要查询的词
    :param return_next: bool 是否获取下一个值
    """
    for index, value in enumerate(contents):
        # 查带有【】的标题的下一个值
        if return_next and query_word in value and '【' in value:
            return contents[index+1]
        # 查询含有查询关键词的内容
        if not return_next and query_word in value:
            return value
    return ''

