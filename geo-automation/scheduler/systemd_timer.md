# 一村科技 GEO 自动化 · systemd 定时（自建服务器推荐）

适合放在公司自有 Linux 服务器上，比 cron 更稳（带日志、失败重试、开机自启）。

## 1) 服务单元 /etc/systemd/system/geo-generate.service
```
[Unit]
Description=Yicun GEO content generator
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/workspace/geo-automation
ExecStart=/usr/bin/python3 generate.py
ExecStartPost=/usr/bin/python3 publish.py
User=www-data
```

## 2) 定时器单元 /etc/systemd/system/geo-generate.timer
```
[Unit]
Description=Run Yicun GEO generator daily at 09:07

[Timer]
OnCalendar=*-*-* 09:07:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
```

## 3) 启用
```
sudo systemctl daemon-reload
sudo systemctl enable --now geo-generate.timer
systemctl list-timers geo-generate.timer   # 查看下次运行时间
journalctl -u geo-generate.service         # 查日志
```
