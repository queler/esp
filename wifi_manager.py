import network
import socket
import ujson
import machine
import time


class WiFiManager:
    CONFIG_FILE = 'wifi.json'

    def __init__(self, ap_ssid=None):
        uid = ''.join('{:02x}'.format(b) for b in machine.unique_id())
        self.ap_ssid = ap_ssid or ('Candle-Setup-' + uid[-4:])
        self.adapter={'sta': network.WLAN(network.STA_IF),
                    'ap': network.WLAN(network.AP_IF)}

    # ---------- Config file helpers ----------
    def _load_config(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                cfg = ujson.load(f)
                if isinstance(cfg, dict) and 'networks' in cfg:
                    return cfg
        except Exception:
            pass
        return {'networks': []}

    def _save_all(self, cfg):
        with open(self.CONFIG_FILE, 'w') as f:
            ujson.dump(cfg, f)

    def _add_or_update_network(self, ssid, password):
        cfg = self._load_config()
        nets = cfg.get('networks', [])
        # update if exists
        for n in nets:
            if n.get('ssid') == ssid:
                n['password'] = password
                self._save_all({'networks': nets})
                return
        # append new
        nets.append({'ssid': ssid, 'password': password})
        self._save_all({'networks': nets})

    def get_saved_networks(self):
        cfg = self._load_config()
        return cfg.get('networks', [])

    # ---------- Scanning & connecting ----------
    def _scan(self):
        sta = self.adapter['sta']
        if not sta.active():
            sta.active(True)
        try:
            scanned = sta.scan()
        except Exception:
            scanned = []
        # scanned entries: (ssid, bssid, channel, RSSI, authmode, hidden)
        result = {}
        for item in scanned:
            ssid = item[0].decode('utf-8') if isinstance(item[0], (bytes, bytearray)) else str(item[0])
            rssi = item[3]
            # keep best rssi per SSID
            if ssid in result:
                if rssi > result[ssid]:
                    result[ssid] = rssi
            else:
                result[ssid] = rssi
        return result

    def connect(self, per_network_timeout=8):
        """Try to connect to saved networks; prefer the strongest available saved network.
        Returns True on success."""
        saved = self.get_saved_networks()
        if not saved:
            return False

        scan_map = self._scan()
        # networks seen with RSSI
        candidates = []
        for n in saved:
            ssid = n.get('ssid')
            pwd = n.get('password', '')
            rssi = scan_map.get(ssid, None)
            candidates.append((ssid, pwd, rssi if rssi is not None else -9999))

        # prefer highest rssi
        candidates.sort(key=lambda x: x[2], reverse=True)

        sta = self.adapter['sta']
        if not sta.active():
            sta.active(True)

        for ssid, pwd, rssi in candidates:
            try:
                print('Trying', ssid, 'rssi', rssi)
                sta.connect(ssid, pwd)
                for _ in range(per_network_timeout):
                    if sta.isconnected():
                        print('Connected to', ssid)
                        return True
                    time.sleep(1)
                # if not connected, disconnect and try next
                try:
                    sta.disconnect()
                except Exception:
                    pass
            except Exception as e:
                print('Error connecting to', ssid, e)
        return sta.isconnected()

    # ---------- Simple URL decode ----------
    def _urldecode(self, s):
        if not s:
            return ''
        s = s.replace('+', ' ')
        res = ''
        i = 0
        L = len(s)
        while i < L:
            ch = s[i]
            if ch == '%' and i + 2 < L:
                try:
                    hexv = s[i+1:i+3]
                    res += chr(int(hexv, 16))
                    i += 3
                    continue
                except Exception:
                    pass
            res += ch
            i += 1
        return res

    # ---------- Config portal (append mode) ----------
    def start_config_portal(self, listen_addr='0.0.0.0', port=80,noap=False):
        # produce a scan snapshot to show available SSIDs
        scans = self._scan()
        ssids = sorted(scans.items(), key=lambda x: x[1], reverse=True)
        if noap or (self.adapter['sta']).isconnected():
            print('Skipping config portal, STA connected')
        else:
            ap = self.adapter['ap']
            ap.active(True)
            ap.config(essid=self.ap_ssid)

        addr = socket.getaddrinfo(listen_addr, port)[0][-1]
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(1)
        if self.adapter['ap'].active():
            print('Config portal running on AP:', self.ap_ssid)
        else:
            print('Config portal running on:', self.adapter['sta'].ipconfig('addr4'))
        html_top = '<html><head><title>WiFi Setup</title></head><body>'
        html_top += '<h3>Select a scanned SSID or enter one manually</h3>'
        html_top += '<form method="post">'
        # dropdown of scanned SSIDs
        html_top += 'Scanned: <select name="ssid_select">'
        html_top += '<option value="">--choose--</option>'
        for ss, r in ssids:
            if self.adapter['sta'].isconnected() and ss == self.adapter['sta'].config('essid'):
                html_top += '<option value="%s">%s ** (%d)</option>' % (ss, ss, r)
            else:
                html_top += '<option value="%s">%s (%d)</option>' % (ss, ss, r)
        html_top += '</select><br>'
        html_top += 'Or SSID: <input name="ssid_manual"><br>'
        html_top += 'Password: <input name="password" type="password"><br>'
        html_top += '<input type="submit" value="Add/Update">'
        html_top += '</form>'
        html_top += '<p>Saved networks:</p><ul>'
        for n in self.get_saved_networks():
            html_top += '<li>%s</li>' % n.get('ssid')
        html_top += '</ul>'
        html_top += '</body></html>'

        try:
            while True:
                cl, addr = s.accept()
                cl_file = cl.makefile('rwb', 0)
                request_line = cl_file.readline()
                if not request_line:
                    cl.close()
                    continue
                # read headers
                headers = b''
                while True:
                    line = cl_file.readline()
                    if not line or line == b'\r\n':
                        break
                    headers += line

                request = request_line.decode('utf-8')
                method = request.split(' ')[0]
                if method == 'GET':
                    resp = 'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n' + html_top
                    cl.send(resp)
                    cl.close()
                    continue

                if method == 'POST':
                    # read body (Content-Length)
                    length = 0
                    try:
                        for hline in headers.split(b'\r\n'):
                            if hline.lower().startswith(b'content-length:'):
                                try:
                                    length = int(hline.split(b':', 1)[1].strip())
                                except Exception:
                                    length = 0
                                break
                    except Exception:
                        length = 0

                    body = cl_file.read(length).decode('utf-8') if length else ''
                    params = {}
                    for pair in body.split('&'):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            params[k] = v

                    ssid = ''
                    if params.get('ssid_manual'):
                        ssid = self._urldecode(params.get('ssid_manual'))
                    elif params.get('ssid_select'):
                        ssid = self._urldecode(params.get('ssid_select'))

                    password = self._urldecode(params.get('password', ''))

                    if ssid:
                        self._add_or_update_network(ssid, password)
                        cl.send('HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n')
                        cl.send('Saved. Rebooting...')
                        cl.close()
                        time.sleep(1)
                        machine.reset()
                    else:
                        cl.send('HTTP/1.0 400 Bad Request\r\n\r\nMissing SSID')
                        cl.close()
        finally:
            try:
                s.close()
            except Exception:
                pass

