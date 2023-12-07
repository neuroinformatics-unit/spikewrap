def lengthOfLongestSubstring(start_str):
    """
    :type s: str
    :rtype: int
    """
    import numpy as np

    np.arange(len(start_str))
    substrings = []
    done_chars = []
    for idx, char in enumerate(start_str):
        if char in done_chars:
            continue

        pos = []
        working_str = start_str
        substr = ""
        for cnt, char2 in enumerate(working_str):
            if char2 == char:
                pos.append(substr)
                substr = ""
            else:
                substr += char2

            if cnt == len(working_str) - 1:
                pos.append(substr)

        for sub in pos:
            if sub != "":
                repeat_within = False
                for perchar in sub:
                    rep_list = [sc for sc in sub if sc == perchar]
                    if len(rep_list) > 1:
                        repeat_within = True
                        break
                if not repeat_within:
                    substrings.append(sub)

    if len(substrings) == 0:
        return 0

    return np.max([len(ss) for ss in substrings]) + 1

    if False:
        substrings = []
        for start_idx in range(len(start_str)):
            for iter_idx in range(len(start_str) - start_idx):
                s = start_str[start_idx : iter_idx + 1]

                subs = ""
                for idx in range(len(s)):
                    if s[idx] in subs:
                        substrings.append(subs)
                        new_subs = ""
                        for prev_s in reversed(subs):
                            if prev_s == s[idx]:
                                break
                            else:
                                new_subs += prev_s
                        subs = new_subs[::-1] + s[idx]

                    else:
                        subs += s[idx]
                        if idx == len(s) - 1:
                            substrings.append(subs)

        if len(substrings) == 0:
            return 0
        lens = [len(str_) for str_ in substrings]
        return np.max(lens)


print(lengthOfLongestSubstring("abcabcbb"))
