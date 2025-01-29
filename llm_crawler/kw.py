def encode_kw(keyword: str) -> str:
    """
    将关键字转换为类似 "kw01L00O80EO062" 这样的混淆编码字符串。
    和前端JS逻辑对应:
      - JS里 ct = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
      - 每个字符转成16位二进制 -> 拼接 -> 每5bit => 1个Base32字符
    :param keyword: 原始关键词，如 "python"
    :return: 带 'kw' 前缀的加密串
    """
    # 自定义的Base32字符表，和JS那边保持完全相同顺序
    ct = "0123456789ABCDEFGHIJKLMNOPQRSTUV"

    # 1. 每个字符 -> 16位二进制
    bin_all = ""
    for ch in keyword:
        # ord(ch) => ASCII / Unicode编码
        ascii_val = ord(ch)
        # 转2进制并补到16位
        bin16 = format(ascii_val, '016b')  # 或 f"{ascii_val:016b}"
        bin_all += bin16

    # 2. 补齐到5的倍数长度
    #   len(bin_all) 可能不是5的倍数，需要补'0'
    pad_length = (len(bin_all) + 4) // 5 * 5
    bin_all = bin_all.ljust(pad_length, '0')

    # 3. 每5位 -> 0~31 的数字 -> ct表里取字符
    encoded_list = []
    for i in range(0, len(bin_all), 5):
        chunk_5 = bin_all[i : i + 5]
        val = int(chunk_5, 2)  # 将二进制字符串转整数
        encoded_list.append(ct[val])

    # 拼成字符串，再加 'kw' 前缀
    encoded_str = "".join(encoded_list)
    return f"kw{encoded_str}"


if __name__ == "__main__":
    # 测试示例
    tests = ["llm", "python", "java 开发", "zlzp","元宇宙","虚拟"]
    for txt in tests:
        print(txt, "=>", encode_kw(txt))