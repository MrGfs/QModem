#!/bin/sh
# /www/cgi-bin/at_rsrp  --  方案A: 经 ubus send_at 取分路信号，绝不直开 /dev/tty*
# 配合 QModem 使用；部署: 放到路由 /www/cgi-bin/at_rsrp, chmod +x, 依赖 jq
#
# 调用:  http://<router>/cgi-bin/at_rsrp?modem1
# 返回:  与 ubus qmodem antenna_signal 同构的 JSON

echo "Content-Type: application/json"
echo ""

SECTION="${QUERY_STRING%%=*}"
[ -z "$SECTION" ] && SECTION="modem1"

# 经 QModem 托管通道透传 AT，返回响应文本
q() {
    ubus call qmodem send_at "{\"config_section\":\"$SECTION\",\"params\":{\"at\":\"$1\"}}" \
        | jq -r '.at_cfg.res // empty'
}

qrsp=$(q "AT+QRSRP?")
qsrq=$(q "AT+QRSRQ?")
qscp=$(q "AT+QRSCP?")
qeng=$(q 'AT+QENG="servingcell"')
qcainfo=$(q "AT+QCAINFO")
qrsgr=$(q "AT+QRSGR?")

arr4() {  # $1=line(+QXXX: a,b,c,d,...)  $2=label
    local line="$1" f i v
    line=$(echo "$line" | sed "s/^+$2: //; s/\r//g; s/ //g")
    for i in 1 2 3 4; do
        v=$(echo "$line" | awk -F',' -v f=$i '{print $f}')
        if [ -n "$v" ] && [ "$v" != "-" ]; then printf '%s' "$v"; else printf '""'; fi
        [ $i -lt 4 ] && printf ','
    done
}
div10() {  # 0.1dB -> dB, 4 路
    local line="$1" f v
    line=$(echo "$line" | sed 's/^+[A-Z]*: //; s/\r//g; s/ //g')
    for i in 1 2 3 4; do
        v=$(echo "$line" | awk -F',' -v f=$i '{print $f}')
        if [ -n "$v" ] && [ "$v" != "-" ]; then awk "BEGIN{printf \"%.1f\", $v/10}"; else printf '""'; fi
        [ $i -lt 4 ] && printf ','
    done
}

rsrp=$(arr4 "$(echo "$qrsp" | grep '+QRSRP:' | head -n1)" "QRSRP")
rsrq=$(div10 "$(echo "$qsrq" | grep '+QRSRQ:' | head -n1)")
scp_line=$(echo "$qscp" | grep '+QRSCP:' | head -n1)
if [ -n "$scp_line" ]; then
    sinr=$(div10 "$scp_line")
else
    ns=$(echo "$qeng" | grep '+QENG: "NR5G-NSA"'); sa=$(echo "$qeng" | grep '+QENG: "NR5G-SA"')
    n=$( [ -n "$ns" ] && echo "$ns" | awk -F',' '{print $6}' || echo "$sa" | awk -F',' '{print $12}' )
    s=""
    for i in 1 2 3 4; do
        [ -n "$n" ] && [ "$n" != "-" ] && s="${s}$(awk "BEGIN{printf \"%.1f\", $n/10}")" || s="${s}\"\""
        [ $i -lt 4 ] && s="${s},"
    done
    sinr="$s"
fi

lte=$(echo "$qeng" | grep '+QENG: "LTE"')
nsa=$(echo "$qeng" | grep '+QENG: "NR5G-NSA"')
sa=$(echo "$qeng" | grep '+QENG: "NR5G-SA"')
if [ -n "$lte" ] && [ -n "$nsa" ]; then netmode=ENDC; rat=NR5G
elif [ -n "$sa" ]; then netmode=SA; rat=NR5G
elif [ -n "$lte" ]; then netmode=LTE; rat=LTE
else netmode=UNKNOWN; rat=UNKNOWN; fi

band=""; pci=""
if [ -n "$nsa" ]; then band=$(echo "$nsa" | awk -F',' '{print $9}'); pci=$(echo "$nsa" | awk -F',' '{print $4}')
elif [ -n "$sa" ]; then band=$(echo "$sa" | awk -F',' '{print $11}'); pci=$(echo "$sa" | awk -F',' '{print $8}'); fi

bw_num=$(echo "$qcainfo" | grep '+QCAINFO:' | grep PCC | awk -F',' '{print $3}' | head -n1)
bw_mhz=""
[ -n "$bw_num" ] && bw_mhz=$(echo "$bw_num" | awk '{ if($1 ~ /^[0-9]+$/) print $1*5+5; else print "" }')
[ -z "$bw_mhz" ] && bw_mhz="\"\""

ca_count=0
echo "$qcainfo" | grep -q '+QCAINFO:' && ca_count=$(echo "$qcainfo" | grep '+QCAINFO:' | grep -E 'PCC|SCC' | wc -l)
[ "$ca_count" -lt 1 ] && ca_count=1

rank=$(echo "$qrsgr" | grep '+QRSGR:' | head -n1 | sed 's/+QRSGR: //; s/\r//g; s/ //g' | awk -F',' '{print $1}')
[ -z "$rank" ] && rank=0

cat <<EOF
{
  "config_section": "$SECTION",
  "timestamp": $(date +%s),
  "antenna_rsrp": [$rsrp],
  "antenna_rsrq": [$rsrq],
  "antenna_sinr": [$sinr],
  "netmode": "$netmode",
  "rat": "$rat",
  "band": "$band",
  "pci": "$pci",
  "bandwidth_mhz": $bw_mhz,
  "ca_count": $ca_count,
  "mimo_rank": $rank
}
EOF
