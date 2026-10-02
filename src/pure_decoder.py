"""Pure-Python QR code decoder, using only the standard library."""

from itertools import combinations, dropwhile
import math


class DecodeError(Exception):
    pass


# One entry per version/level in the order L, M, Q, H. Each entry contains one
# or more block groups as flat triples: (block count, total codewords, data codewords).
_RS_BLOCK_TABLE = (
    (1, 26, 19), (1, 26, 16), (1, 26, 13), (1, 26, 9),
    (1, 44, 34), (1, 44, 28), (1, 44, 22), (1, 44, 16),
    (1, 70, 55), (1, 70, 44), (2, 35, 17), (2, 35, 13),
    (1, 100, 80), (2, 50, 32), (2, 50, 24), (4, 25, 9),
    (1, 134, 108), (2, 67, 43), (2, 33, 15, 2, 34, 16), (2, 33, 11, 2, 34, 12),
    (2, 86, 68), (4, 43, 27), (4, 43, 19), (4, 43, 15),
    (2, 98, 78), (4, 49, 31), (2, 32, 14, 4, 33, 15), (4, 39, 13, 1, 40, 14),
    (2, 121, 97), (2, 60, 38, 2, 61, 39), (4, 40, 18, 2, 41, 19), (4, 40, 14, 2, 41, 15),
    (2, 146, 116), (3, 58, 36, 2, 59, 37), (4, 36, 16, 4, 37, 17), (4, 36, 12, 4, 37, 13),
    (2, 86, 68, 2, 87, 69), (4, 69, 43, 1, 70, 44), (6, 43, 19, 2, 44, 20), (6, 43, 15, 2, 44, 16),
    (4, 101, 81), (1, 80, 50, 4, 81, 51), (4, 50, 22, 4, 51, 23), (3, 36, 12, 8, 37, 13),
    (2, 116, 92, 2, 117, 93), (6, 58, 36, 2, 59, 37), (4, 46, 20, 6, 47, 21), (7, 42, 14, 4, 43, 15),
    (4, 133, 107), (8, 59, 37, 1, 60, 38), (8, 44, 20, 4, 45, 21), (12, 33, 11, 4, 34, 12),
    (3, 145, 115, 1, 146, 116), (4, 64, 40, 5, 65, 41), (11, 36, 16, 5, 37, 17), (11, 36, 12, 5, 37, 13),
    (5, 109, 87, 1, 110, 88), (5, 65, 41, 5, 66, 42), (5, 54, 24, 7, 55, 25), (11, 36, 12, 7, 37, 13),
    (5, 122, 98, 1, 123, 99), (7, 73, 45, 3, 74, 46), (15, 43, 19, 2, 44, 20), (3, 45, 15, 13, 46, 16),
    (1, 135, 107, 5, 136, 108), (10, 74, 46, 1, 75, 47), (1, 50, 22, 15, 51, 23), (2, 42, 14, 17, 43, 15),
    (5, 150, 120, 1, 151, 121), (9, 69, 43, 4, 70, 44), (17, 50, 22, 1, 51, 23), (2, 42, 14, 19, 43, 15),
    (3, 141, 113, 4, 142, 114), (3, 70, 44, 11, 71, 45), (17, 47, 21, 4, 48, 22), (9, 39, 13, 16, 40, 14),
    (3, 135, 107, 5, 136, 108), (3, 67, 41, 13, 68, 42), (15, 54, 24, 5, 55, 25), (15, 43, 15, 10, 44, 16),
    (4, 144, 116, 4, 145, 117), (17, 68, 42), (17, 50, 22, 6, 51, 23), (19, 46, 16, 6, 47, 17),
    (2, 139, 111, 7, 140, 112), (17, 74, 46), (7, 54, 24, 16, 55, 25), (34, 37, 13),
    (4, 151, 121, 5, 152, 122), (4, 75, 47, 14, 76, 48), (11, 54, 24, 14, 55, 25), (16, 45, 15, 14, 46, 16),
    (6, 147, 117, 4, 148, 118), (6, 73, 45, 14, 74, 46), (11, 54, 24, 16, 55, 25), (30, 46, 16, 2, 47, 17),
    (8, 132, 106, 4, 133, 107), (8, 75, 47, 13, 76, 48), (7, 54, 24, 22, 55, 25), (22, 45, 15, 13, 46, 16),
    (10, 142, 114, 2, 143, 115), (19, 74, 46, 4, 75, 47), (28, 50, 22, 6, 51, 23), (33, 46, 16, 4, 47, 17),
    (8, 152, 122, 4, 153, 123), (22, 73, 45, 3, 74, 46), (8, 53, 23, 26, 54, 24), (12, 45, 15, 28, 46, 16),
    (3, 147, 117, 10, 148, 118), (3, 73, 45, 23, 74, 46), (4, 54, 24, 31, 55, 25), (11, 45, 15, 31, 46, 16),
    (7, 146, 116, 7, 147, 117), (21, 73, 45, 7, 74, 46), (1, 53, 23, 37, 54, 24), (19, 45, 15, 26, 46, 16),
    (5, 145, 115, 10, 146, 116), (19, 75, 47, 10, 76, 48), (15, 54, 24, 25, 55, 25), (23, 45, 15, 25, 46, 16),
    (13, 145, 115, 3, 146, 116), (2, 74, 46, 29, 75, 47), (42, 54, 24, 1, 55, 25), (23, 45, 15, 28, 46, 16),
    (17, 145, 115), (10, 74, 46, 23, 75, 47), (10, 54, 24, 35, 55, 25), (19, 45, 15, 35, 46, 16),
    (17, 145, 115, 1, 146, 116), (14, 74, 46, 21, 75, 47), (29, 54, 24, 19, 55, 25), (11, 45, 15, 46, 46, 16),
    (13, 145, 115, 6, 146, 116), (14, 74, 46, 23, 75, 47), (44, 54, 24, 7, 55, 25), (59, 46, 16, 1, 47, 17),
    (12, 151, 121, 7, 152, 122), (12, 75, 47, 26, 76, 48), (39, 54, 24, 14, 55, 25), (22, 45, 15, 41, 46, 16),
    (6, 151, 121, 14, 152, 122), (6, 75, 47, 34, 76, 48), (46, 54, 24, 10, 55, 25), (2, 45, 15, 64, 46, 16),
    (17, 152, 122, 4, 153, 123), (29, 74, 46, 14, 75, 47), (49, 54, 24, 10, 55, 25), (24, 45, 15, 46, 46, 16),
    (4, 152, 122, 18, 153, 123), (13, 74, 46, 32, 75, 47), (48, 54, 24, 14, 55, 25), (42, 45, 15, 32, 46, 16),
    (20, 147, 117, 4, 148, 118), (40, 75, 47, 7, 76, 48), (43, 54, 24, 22, 55, 25), (10, 45, 15, 67, 46, 16),
    (19, 148, 118, 6, 149, 119), (18, 75, 47, 31, 76, 48), (34, 54, 24, 34, 55, 25), (20, 45, 15, 61, 46, 16),
)


_ALIGNMENT_POSITIONS = (
    (),
    (6, 18),
    (6, 22),
    (6, 26),
    (6, 30),
    (6, 34),
    (6, 22, 38),
    (6, 24, 42),
    (6, 26, 46),
    (6, 28, 50),
    (6, 30, 54),
    (6, 32, 58),
    (6, 34, 62),
    (6, 26, 46, 66),
    (6, 26, 48, 70),
    (6, 26, 50, 74),
    (6, 30, 54, 78),
    (6, 30, 56, 82),
    (6, 30, 58, 86),
    (6, 34, 62, 90),
    (6, 28, 50, 72, 94),
    (6, 26, 50, 74, 98),
    (6, 30, 54, 78, 102),
    (6, 28, 54, 80, 106),
    (6, 32, 58, 84, 110),
    (6, 30, 58, 86, 114),
    (6, 34, 62, 90, 118),
    (6, 26, 50, 74, 98, 122),
    (6, 30, 54, 78, 102, 126),
    (6, 26, 52, 78, 104, 130),
    (6, 30, 56, 82, 108, 134),
    (6, 34, 60, 86, 112, 138),
    (6, 30, 58, 86, 114, 142),
    (6, 34, 62, 90, 118, 146),
    (6, 30, 54, 78, 102, 126, 150),
    (6, 24, 50, 76, 102, 128, 154),
    (6, 28, 54, 80, 106, 132, 158),
    (6, 32, 58, 84, 110, 136, 162),
    (6, 26, 54, 82, 110, 138, 166),
    (6, 30, 58, 86, 114, 142, 170),
)


_ALPHANUMERIC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"


def _make_gf_tables():
    exp = [0] * 512
    log = [0] * 256
    value = 1
    for i in range(255):
        exp[i] = value
        log[value] = i
        value <<= 1
        if value & 0x100:
            value ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_GF_EXP, _GF_LOG = _make_gf_tables()


def _gf_mul(a, b):
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _gf_inverse(a):
    if a == 0:
        raise DecodeError("Cannot invert zero")
    return _GF_EXP[255 - _GF_LOG[a]]


def _gf_pow(a, power):
    if a == 0:
        return 0
    return _GF_EXP[(_GF_LOG[a] * (power % 255)) % 255]


def _gf_sub(a, b):
    return a ^ b


def _gf_div(a, b):
    if b == 0:
        raise DecodeError("Division by zero")
    return _gf_mul(a, _gf_inverse(b))


def _poly_scale(poly, x):
    return [_gf_mul(c, x) for c in poly]


def _poly_add(p, q):
    result = [0] * max(len(p), len(q))
    result[len(result) - len(p):len(result)] = p
    for i in range(len(q)):
        result[i + len(result) - len(q)] ^= q[i]
    return result


def _poly_mul(p, q):
    result = [0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        if a:
            log_a = _GF_LOG[a]
            for j, b in enumerate(q):
                if b:
                    result[i + j] ^= _GF_EXP[log_a + _GF_LOG[b]]
    return result


def _poly_div(dividend, divisor):
    msg = list(dividend)
    for i in range(len(dividend) - (len(divisor) - 1)):
        coef = msg[i]
        if coef:
            for j in range(1, len(divisor)):
                if divisor[j]:
                    msg[i + j] ^= _gf_mul(divisor[j], coef)
    separator = -(len(divisor) - 1)
    return msg[:separator], msg[separator:]


def _poly_eval(poly, x):
    y = poly[0]
    for i in range(1, len(poly)):
        y = _gf_mul(y, x) ^ poly[i]
    return y


def _rs_calc_syndromes(msg, nsym):
    return [0] + [_poly_eval(msg, _gf_pow(2, i)) for i in range(nsym)]


def _rs_find_errata_locator(e_pos):
    loc = [1]
    for pos in e_pos:
        loc = _poly_mul(loc, _poly_add([1], [_gf_pow(2, pos), 0]))
    return loc


def _rs_find_error_evaluator(synd, err_loc, nsym):
    _, remainder = _poly_div(_poly_mul(synd, err_loc), [1] + [0] * (nsym + 1))
    return remainder


def _rs_correct_errata(msg_in, synd, err_pos):
    msg = list(msg_in)
    coef_pos = [len(msg) - 1 - p for p in err_pos]
    err_loc = _rs_find_errata_locator(coef_pos)
    err_eval = _rs_find_error_evaluator(synd[::-1], err_loc, len(err_loc) - 1)[::-1]
    x_values = [_gf_pow(2, -(255 - pos)) for pos in coef_pos]
    magnitudes = [0] * len(msg)
    for i, xi in enumerate(x_values):
        xi_inv = _gf_inverse(xi)
        product = 1
        for j, xj in enumerate(x_values):
            if i != j:
                product = _gf_mul(product, _gf_sub(1, _gf_mul(xi_inv, xj)))
        y = _poly_eval(err_eval[::-1], xi_inv)
        y = _gf_mul(xi, y)
        magnitudes[err_pos[i]] = _gf_div(y, product)
    return _poly_add(msg, magnitudes)


def _rs_find_error_locator(synd, nsym):
    err_loc = [1]
    old_loc = [1]
    for i in range(nsym):
        delta = synd[i]
        for j in range(1, len(err_loc)):
            delta ^= _gf_mul(err_loc[-(j + 1)], synd[i - j])
        old_loc.append(0)
        if delta:
            if len(old_loc) > len(err_loc):
                new_loc = _poly_scale(old_loc, delta)
                old_loc = _poly_scale(err_loc, _gf_inverse(delta))
                err_loc = new_loc
            err_loc = _poly_add(err_loc, _poly_scale(old_loc, delta))
    err_loc = list(dropwhile(lambda x: x == 0, err_loc))
    if (len(err_loc) - 1) * 2 > nsym:
        raise DecodeError("Too many errors to correct")
    return err_loc


def _rs_find_errors(err_loc, nmess):
    errs = len(err_loc) - 1
    positions = []
    for i in range(nmess):
        if _poly_eval(err_loc, _gf_pow(2, i)) == 0:
            positions.append(nmess - 1 - i)
    if len(positions) != errs:
        raise DecodeError("Error locator root count mismatch")
    return positions


def _rs_correct(msg, nsym):
    msg = list(msg)
    synd = _rs_calc_syndromes(msg, nsym)
    if max(synd) == 0:
        return msg[:-nsym]
    err_loc = _rs_find_error_locator(list(synd[1:]), nsym)
    err_pos = _rs_find_errors(err_loc[::-1], len(msg))
    msg = _rs_correct_errata(msg, synd, err_pos)
    if max(_rs_calc_syndromes(msg, nsym)) > 0:
        raise DecodeError("Reed-Solomon correction failed")
    return msg[:-nsym]


def _block_specs(version, level_index):
    entry = _RS_BLOCK_TABLE[(version - 1) * 4 + level_index]
    return [
        (entry[i], entry[i + 1], entry[i + 2])
        for i in range(0, len(entry), 3)
    ]


def _block_layout(version, level_index):
    specs = _block_specs(version, level_index)
    blocks = []
    data_codewords = 0
    for count, total, data in specs:
        blocks.extend([(total, data)] * count)
        data_codewords += count * data
    ec_codewords = blocks[0][0] - blocks[0][1]
    return blocks, data_codewords, ec_codewords


def _otsu_threshold(gray):
    histogram = [0] * 256
    for row in gray:
        for value in row:
            histogram[value] += 1
    total = sum(histogram)
    if total == 0:
        return 128
    sum_total = sum(i * count for i, count in enumerate(histogram))
    sum_back = 0
    weight_back = 0
    best = 128
    best_variance = -1.0
    for threshold in range(256):
        weight_back += histogram[threshold]
        if weight_back == 0:
            continue
        weight_front = total - weight_back
        if weight_front == 0:
            break
        sum_back += threshold * histogram[threshold]
        mean_back = sum_back / weight_back
        mean_front = (sum_total - sum_back) / weight_front
        variance = (
            weight_back
            * weight_front
            * (mean_back - mean_front)
            * (mean_back - mean_front)
        )
        if variance > best_variance:
            best_variance = variance
            best = threshold
    return best


def _binarize(gray, threshold, dark_is_black=True):
    rows = []
    for row in gray:
        if dark_is_black:
            rows.append(bytes(1 if value <= threshold else 0 for value in row))
        else:
            rows.append(bytes(1 if value > threshold else 0 for value in row))
    return rows


def _is_finder_pattern(lengths):
    total = sum(lengths)
    if total < 7:
        return False
    scale = 7.0 / total
    expected = (1, 1, 3, 1, 1)
    return all(abs(value * scale - wanted) <= 0.6 for value, wanted in zip(lengths, expected))


def _vertical_ok(binary, x, y):
    height = len(binary)
    color = binary[y][x]
    if color != 1:
        return False
    up = 0
    yy = y
    while yy >= 0 and binary[yy][x] == color:
        up += 1
        yy -= 1
    down = 0
    yy = y + 1
    while yy < height and binary[yy][x] == color:
        down += 1
        yy += 1
    center = up + down
    white1 = 0
    yy = y - up - 1
    while yy >= 0 and binary[yy][x] == 0:
        white1 += 1
        yy -= 1
    black1 = 0
    while yy >= 0 and binary[yy][x] == 1:
        black1 += 1
        yy -= 1
    white2 = 0
    yy = y + down + 1
    while yy < height and binary[yy][x] == 0:
        white2 += 1
        yy += 1
    black2 = 0
    while yy < height and binary[yy][x] == 1:
        black2 += 1
        yy += 1
    return _is_finder_pattern([black1, white1, center, white2, black2])


def _find_finder_centers(binary):
    height = len(binary)
    width = len(binary[0])
    centers = []
    for y in range(height):
        row = binary[y]
        runs = []
        start = 0
        color = row[0]
        for x in range(1, width):
            if row[x] != color:
                runs.append((start, x - 1, color))
                start = x
                color = row[x]
        runs.append((start, width - 1, color))
        for i in range(2, len(runs) - 2):
            color = runs[i][2]
            if color != 1:
                continue
            lengths = (
                runs[i - 2][1] - runs[i - 2][0] + 1,
                runs[i - 1][1] - runs[i - 1][0] + 1,
                runs[i][1] - runs[i][0] + 1,
                runs[i + 1][1] - runs[i + 1][0] + 1,
                runs[i + 2][1] - runs[i + 2][0] + 1,
            )
            if not _is_finder_pattern(lengths):
                continue
            start, end, _ = runs[i]
            center_x = (start + end) / 2.0
            if _vertical_ok(binary, int(round(center_x)), y):
                centers.append((center_x, y, (end - start + 1) / 3.0))
    clusters = []
    for x, y, module in centers:
        best = None
        best_distance = None
        for index, (cx, cy, cm, count) in enumerate(clusters):
            distance = math.hypot(x - cx, y - cy)
            radius = max(module, cm) * 1.8
            if distance <= radius and (best_distance is None or distance < best_distance):
                best = index
                best_distance = distance
        if best is None:
            clusters.append([x, y, module, 1])
        else:
            cx, cy, cm, count = clusters[best]
            clusters[best] = [
                (cx * count + x) / (count + 1),
                (cy * count + y) / (count + 1),
                (cm * count + module) / (count + 1),
                count + 1,
            ]
    result = sorted(
        ((cx, cy, cm, count) for cx, cy, cm, count in clusters),
        key=lambda item: item[3],
        reverse=True,
    )
    return [(cx, cy, cm) for cx, cy, cm, _ in result[:40]]


def _similar(a, b, tolerance):
    return abs(a - b) <= tolerance * max(a, b, 1.0)


def _right_angle_options(triple):
    for corner in triple:
        others = [p for p in triple if p is not corner]
        side1 = math.hypot(others[0][0] - corner[0], others[0][1] - corner[1])
        side2 = math.hypot(others[1][0] - corner[0], others[1][1] - corner[1])
        diagonal = math.hypot(others[0][0] - others[1][0], others[0][1] - others[1][1])
        if (
            _similar(side1, side2, 0.25)
            and _similar(diagonal, math.hypot(side1, side2), 0.35)
            and side1 >= 14.0
        ):
            yield corner, others[0], others[1], (side1 + side2) / 2.0


def _sample_matrix(binary, size, origin, right, down, mirror_u, mirror_v):
    height = len(binary)
    width = len(binary[0])
    denominator = size - 7
    matrix = []
    for v in range(size):
        qv = size - 1 - v if mirror_v else v
        row = []
        for u in range(size):
            qu = size - 1 - u if mirror_u else u
            uu = qu + 0.5 - 3.5
            vv = qv + 0.5 - 3.5
            x = origin[0] + (right[0] - origin[0]) * uu / denominator
            x += (down[0] - origin[0]) * vv / denominator
            y = origin[1] + (right[1] - origin[1]) * uu / denominator
            y += (down[1] - origin[1]) * vv / denominator
            px = max(0, min(width - 1, int(round(x))))
            py = max(0, min(height - 1, int(round(y))))
            row.append(binary[py][px])
        matrix.append(row)
    return matrix


def _format_positions(size):
    vertical = [(i, 8) for i in range(6)]
    vertical += [(7, 8), (8, 8)]
    vertical += [(size - 15 + i, 8) for i in range(8, 15)]
    horizontal = [(8, size - 1 - i) for i in range(8)]
    horizontal += [(8, 7)]
    horizontal += [(8, 14 - i) for i in range(9, 15)]
    return vertical, horizontal


def _bch_remainder(value):
    rem = value
    for bit in range(14, 9, -1):
        if rem & (1 << bit):
            rem ^= 0x537 << (bit - 10)
    return rem


_FORMAT_CODES = []
for _ec_bits in range(4):
    for _mask in range(8):
        _data = (_ec_bits << 3) | _mask
        _code = (_data << 10) | _bch_remainder(_data << 10)
        _code ^= 0x5412
        _FORMAT_CODES.append((_code, _ec_bits, _mask))


_EC_BITS_TO_INDEX = {0b01: 0, 0b00: 1, 0b11: 2, 0b10: 3}


def _decode_format(matrix, size):
    positions = _format_positions(size)
    observed = []
    for row, col in positions[0] + positions[1]:
        observed.append(1 if matrix[row][col] else 0)
    best = None
    best_distance = 99
    for code, ec_bits, mask in _FORMAT_CODES:
        distance = 0
        for bit_index in range(15):
            wanted = (code >> bit_index) & 1
            for copy in range(2):
                if observed[copy * 15 + bit_index] != wanted:
                    distance += 1
        if distance < best_distance:
            best_distance = distance
            best = (ec_bits, mask)
    if best is None or best_distance > 3:
        raise DecodeError("Format information is too damaged")
    return _EC_BITS_TO_INDEX[best[0]], best[1]


def _alignment_centers(version):
    return _ALIGNMENT_POSITIONS[version - 1]


def _build_function_matrix(size):
    version = (size - 17) // 4
    function = [[False] * size for _ in range(size)]

    def mark_rect(row0, col0, rows, cols):
        for row in range(row0, row0 + rows):
            for col in range(col0, col0 + cols):
                if 0 <= row < size and 0 <= col < size:
                    function[row][col] = True

    mark_rect(0, 0, 8, 8)
    mark_rect(0, size - 8, 8, 8)
    mark_rect(size - 8, 0, 8, 8)

    for col in range(8, size - 8):
        function[6][col] = True
    for row in range(8, size - 8):
        function[row][6] = True

    centers = _alignment_centers(version)
    for row_center in centers:
        for col_center in centers:
            if (
                (row_center == 6 and col_center == 6)
                or (row_center == 6 and col_center == size - 7)
                or (row_center == size - 7 and col_center == 6)
            ):
                continue
            mark_rect(row_center - 2, col_center - 2, 5, 5)

    for row, col in _format_positions(size)[0] + _format_positions(size)[1]:
        function[row][col] = True

    if version >= 7:
        for i in range(6):
            for j in range(3):
                function[size - 11 + j][i] = True
                function[i][size - 11 + j] = True

    function[4 * version + 9][8] = True
    return function


def _mask_applies(mask, row, col):
    product = row * col
    if mask == 0:
        return (row + col) % 2 == 0
    if mask == 1:
        return row % 2 == 0
    if mask == 2:
        return col % 3 == 0
    if mask == 3:
        return (row + col) % 3 == 0
    if mask == 4:
        return (row // 2 + col // 3) % 2 == 0
    if mask == 5:
        return product % 2 + product % 3 == 0
    if mask == 6:
        return (product % 2 + product % 3) % 2 == 0
    return ((row + col) % 2 + product % 3) % 2 == 0


def _read_codewords(matrix, function):
    size = len(matrix)
    bits = []
    col = size - 1
    going_up = True
    while col > 0:
        if col == 6:
            col -= 1
            continue
        col_pair = (col, col - 1)
        row = size - 1 if going_up else 0
        step = -1 if going_up else 1
        while 0 <= row < size:
            for current_col in col_pair:
                if not function[row][current_col]:
                    bits.append(matrix[row][current_col])
            row += step
        going_up = not going_up
        col -= 2
    codewords = []
    for i in range(0, len(bits) - 7, 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        codewords.append(byte)
    return codewords


def _correct_codewords(codewords, version, level_index):
    blocks, data_codewords, ec_codewords = _block_layout(version, level_index)
    total_needed = data_codewords + ec_codewords * len(blocks)
    if len(codewords) < total_needed:
        raise DecodeError("Not enough codewords")
    raw = codewords[:total_needed]
    max_data = max(data for _, data in blocks)
    data_parts = [[] for _ in blocks]
    offset = 0
    for i in range(max_data):
        for block_index, (_, data) in enumerate(blocks):
            if i < data:
                data_parts[block_index].append(raw[offset])
                offset += 1
    ecc_parts = [[] for _ in blocks]
    for i in range(ec_codewords):
        for block_index in range(len(blocks)):
            ecc_parts[block_index].append(raw[offset])
            offset += 1
    corrected = []
    for block_index, (_, data) in enumerate(blocks):
        block = data_parts[block_index] + ecc_parts[block_index]
        corrected.append(_rs_correct(block, ec_codewords))
    result = []
    for i in range(max_data):
        for block_index in range(len(blocks)):
            if i < len(corrected[block_index]):
                result.append(corrected[block_index][i])
    return result


class _BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, count):
        if self.pos + count > len(self.data) * 8:
            raise DecodeError("Unexpected end of data stream")
        value = 0
        for _ in range(count):
            byte = self.data[self.pos // 8]
            bit = (byte >> (7 - (self.pos % 8))) & 1
            value = (value << 1) | bit
            self.pos += 1
        return value

    def remaining(self):
        return len(self.data) * 8 - self.pos


def _count_bits(mode, version):
    table = {
        1: (10, 12, 14),
        2: (9, 11, 13),
        4: (8, 16, 16),
        8: (8, 10, 12),
    }
    if version <= 9:
        index = 0
    elif version <= 26:
        index = 1
    else:
        index = 2
    return table[mode][index]


def _read_numeric(reader, count, output):
    while count >= 3:
        value = reader.read(10)
        if value >= 1000:
            raise DecodeError("Invalid numeric group")
        output.extend(f"{value:03d}".encode("ascii"))
        count -= 3
    if count == 2:
        value = reader.read(7)
        if value >= 100:
            raise DecodeError("Invalid numeric group")
        output.extend(f"{value:02d}".encode("ascii"))
    elif count == 1:
        value = reader.read(4)
        if value >= 10:
            raise DecodeError("Invalid numeric group")
        output.append(48 + value)


def _read_alphanumeric(reader, count, output):
    while count >= 2:
        value = reader.read(11)
        if value >= 45 * 45:
            raise DecodeError("Invalid alphanumeric pair")
        output.append(ord(_ALPHANUMERIC[value // 45]))
        output.append(ord(_ALPHANUMERIC[value % 45]))
        count -= 2
    if count == 1:
        value = reader.read(6)
        if value >= 45:
            raise DecodeError("Invalid alphanumeric value")
        output.append(ord(_ALPHANUMERIC[value]))


def _read_kanji(reader, count, output):
    for _ in range(count):
        value = reader.read(13)
        decoded = (value // 0xC0) << 8 | (value % 0xC0)
        if decoded < 0x1F00:
            decoded += 0x8140
        else:
            decoded += 0xC140
        output.extend(decoded.to_bytes(2, "big"))


def _read_eci(reader):
    first = reader.read(1)
    if first == 0:
        return reader.read(7)
    second = reader.read(1)
    if second == 0:
        return reader.read(14)
    third = reader.read(1)
    if third != 1:
        raise DecodeError("Invalid ECI designator")
    return reader.read(21)


def _decode_bytes(raw, eci):
    if eci is not None:
        if eci == 26:
            return raw.decode("utf-8", "replace")
        if eci in (0, 1, 2):
            return raw.decode("cp437", "replace")
        if eci == 20:
            return raw.decode("shift_jis", "replace")
        if 3 <= eci <= 25:
            try:
                return raw.decode(f"iso8859-{eci - 2}", "replace")
            except LookupError:
                pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("shift_jis")
        except UnicodeDecodeError:
            return raw.decode("latin-1")


def _parse_data(data, version):
    reader = _BitReader(data)
    output = bytearray()
    eci = None
    while reader.remaining() >= 4:
        mode = reader.read(4)
        if mode == 0:
            break
        if mode == 1:
            count = reader.read(_count_bits(1, version))
            _read_numeric(reader, count, output)
        elif mode == 2:
            count = reader.read(_count_bits(2, version))
            _read_alphanumeric(reader, count, output)
        elif mode == 4:
            count = reader.read(_count_bits(4, version))
            for _ in range(count):
                output.append(reader.read(8))
        elif mode == 8:
            count = reader.read(_count_bits(8, version))
            _read_kanji(reader, count, output)
        elif mode == 7:
            eci = _read_eci(reader)
        elif mode in (3, 5, 9):
            if mode == 3:
                reader.read(16)
        else:
            break
    return _decode_bytes(bytes(output), eci)


def _decode_matrix(matrix, size):
    version = (size - 17) // 4
    if version < 1 or version > 40:
        raise DecodeError("Unsupported QR version")
    level_index, mask = _decode_format(matrix, size)
    function = _build_function_matrix(size)
    unmasked = [list(row) for row in matrix]
    for row in range(size):
        for col in range(size):
            if not function[row][col] and _mask_applies(mask, row, col):
                unmasked[row][col] ^= 1
    codewords = _read_codewords(unmasked, function)
    data = _correct_codewords(codewords, version, level_index)
    return _parse_data(data, version)


def decode_binary(binary):
    centers = _find_finder_centers(binary)
    if len(centers) < 3:
        return None
    for triple in combinations(centers, 3):
        for origin, right, down, side in _right_angle_options(triple):
            module = origin[2]
            estimated_size = round(side / module + 7)
            for size in range(max(21, estimated_size - 6), min(177, estimated_size + 6) + 1):
                variants = (
                    (right, down, False, False),
                    (down, right, False, False),
                    (right, down, True, False),
                    (down, right, True, False),
                    (right, down, False, True),
                    (down, right, False, True),
                    (right, down, True, True),
                    (down, right, True, True),
                )
                for endpoint_u, endpoint_v, mirror_u, mirror_v in variants:
                    matrix = _sample_matrix(
                        binary,
                        size,
                        origin,
                        endpoint_u,
                        endpoint_v,
                        mirror_u,
                        mirror_v,
                    )
                    try:
                        return _decode_matrix(matrix, size)
                    except (DecodeError, IndexError, ValueError):
                        continue
    return None


def decode_gray(gray):
    """Decode one QR code from rows of grayscale pixel values 0-255."""
    if not gray or not gray[0]:
        return None
    threshold = _otsu_threshold(gray)
    binary = _binarize(gray, threshold, True)
    text = decode_binary(binary)
    if text is not None:
        return text
    inverted = _binarize(gray, threshold, False)
    return decode_binary(inverted)


def decode_rgb(rgb):
    """Decode one QR code from rows of (red, green, blue) tuples."""
    gray = [
        bytes(
            int(round(0.299 * r + 0.587 * g + 0.114 * b))
            for r, g, b in row
        )
        for row in rgb
    ]
    return decode_gray(gray)
