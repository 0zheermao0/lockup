~~ 仔细研究了一下 大概并不推荐自建邮件服务器吧 所以这个文档大概就看看就行了 大概并没有什么用~~

### 确认运营商允许发起dstport=25的tcp连接
处于安全原因 很多运营商不允许连接到其他服务器的25号端口 需要测试一下
```
nc -vz gmail-smtp-in.l.google.com 25
```
如果不行那就寄了吧 大概

### 请确保25号端口的inbound是关闭的 不然可能会被黑名单 或者被坏人当作relay利用
rt

### 安装postfix
```
sudo apt update && sudo apt install postfix
vim /etc/postfix/main.cf
```

### 配置postfix
```
# 基本身份
myhostname = lock-up.zheermao.top
myorigin = lock-up.zheermao.top

# 只监听本地（非常重要）
inet_interfaces = loopback-only
inet_protocols = ipv4

# 不接收任何域的邮件
mydestination =

# 只允许本机 relay
mynetworks = 127.0.0.0/8

# 防止 open relay（非常重要）
smtpd_recipient_restrictions =
    permit_mynetworks,
    reject_unauth_destination

# 禁用本地收件人检查（非常关键）
local_recipient_maps =

# 禁用本地别名扩展
alias_maps =
alias_database =

# 强制所有非本机投递走 SMTP
default_transport = smtp
relay_transport = smtp

```


### 配置dns record
- 如果不配只dns record 在多数的email provider会认为这个电子邮件是一个未经验证的邮件 所以会拒收
- 如果完成了mailgun的dns配置 那么你的邮件服务器地址应该有一个对应的TXT记录如下：
```
lock-up.domain.name. 3600 IN  TXT     "v=spf1 include:mailgun.org ~all"
```
- 为了使本地的地址也被认为是一个经过认证的邮件源 添加 `a lock-up.domain.name ` 字段，如下 (但是大概需要lock-up.domain.name绑定到真实机器的ip地址 如果开了proxy可能要写成ip4:xxxxxx)
```
lock-up.domain.name. 3600 IN  TXT     "v=spf1 a:lock-up.domain.name include:mailgun.org ~all"
```
- 修改之后需要等到1-30分钟 因为接收方的邮件服务器需要更新可信源


### 测试postfix是否联通
```
printf "From: noreply@lock-up.domain.name\n\
    To: reciever@email.addr\n\
    Subject: raw smtp test\n\n\
    hello\n" | sendmail -v reciever@email.addr
```
以及大概你可以设置To和收信地址不同 会产生一些奇妙的邮件
