# PostgreSQL + SSL 인증 기반 외부 접속 환경 구축 문서

## 1. 서버 측 PostgreSQL 설치 및 기본 설정

### 목적
PostgreSQL 설치 후 외부 접속이 가능한 상태로 설정하며, SSL 통신을 적용하기 위한 준비 과정.

### 과정
```bash
# PostgreSQL 설치
sudo apt update
sudo apt install postgresql postgresql-contrib

# PostgreSQL 서비스 확인 및 활성화
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl status postgresql

# 방화벽 설정
sudo ufw allow 5432/tcp   # PostgreSQL 포트 오픈
sudo ufw reload

# PostgreSQL이 모든 IP에서 접속 허용하도록 설정
sudo vim /etc/postgresql/14/main/postgresql.conf
listen_addresses = '*'

# pg_hba.conf 수정 (초기에는 md5 또는 scram-sha-256으로 설정)
sudo vim /etc/postgresql/14/main/pg_hba.conf
host    all             all             0.0.0.0/0            md5

# PostgreSQL 재시작
sudo systemctl restart postgresql
```

---

## 2. 인증서 생성 및 배포

### 목적
PostgreSQL 서버와 클라이언트가 상호 인증을 통해 신뢰할 수 있는 SSL 연결을 구축.

### 서버 측 (PostgreSQL 서버)
- **서버 역할**: PostgreSQL 서비스를 제공하는 서버
- **DB 유저**: `DB_USER` (예: `jinu`)는 PostgreSQL에서 생성한 사용자 계정이며, 인증 및 권한 부여에 사용됨

```bash
# SSL 디렉토리 생성
sudo mkdir -p /etc/postgresql/ssl
cd /etc/postgresql/ssl

# 서버 인증서 및 키 생성
sudo openssl req -new -x509 -days 365 -nodes -text \
  -out server.crt -keyout server.key \
  -subj "/CN=서버도메인"

sudo chmod 600 server.key
sudo chown postgres:postgres server.*

# 클라이언트 인증서 및 키 생성 (CN=DB_USER)
sudo openssl genrsa -out DB_USER.key 2048
sudo openssl req -new -key DB_USER.key -out DB_USER.csr -subj "/CN=DB_USER"
sudo openssl x509 -req -in DB_USER.csr -CA server.crt -CAkey server.key -CAcreateserial -out DB_USER.crt -days 365 -sha256
sudo chown postgres:postgres DB_USER.*
```

### 클라이언트 측 (호스트, ex. macOS)
- **호스트 역할**: PostgreSQL에 접속하는 외부 클라이언트 환경

```bash
mkdir -p ~/.postgresql
scp -P 포트번호 서버계정@서버주소:/etc/postgresql/ssl/DB_USER.* ~/.postgresql/
scp -P 포트번호 서버계정@서버주소:/etc/postgresql/ssl/server.crt ~/.postgresql/root.crt

# 권한 설정
chmod 600 ~/.postgresql/DB_USER.key
chmod 644 ~/.postgresql/DB_USER.crt
chmod 644 ~/.postgresql/root.crt
```

### 서버 pg_hba.conf 수정
```bash
# /etc/postgresql/14/main/pg_hba.conf
hostssl all all 0.0.0.0/0 cert clientcert=verify-full
```

### PostgreSQL 재시작
```bash
sudo systemctl restart postgresql
```

---

## 3. PgAdmin4 설정 (클라이언트)

### 목적
GUI 환경에서 PostgreSQL 서버를 접속 및 관리하기 위함.

### 설정 방법
1. `General`
   - Name : 임의의 이름
2. `Connection`
   - Host: 서버의 도메인 또는 IP
   - Port: 5432
   - Maintenance DB: postgres
   - Username: DB_USER (ex: jinu)
   - Password: DB_USER의 비밀번호
3. `SSL`
   - SSL Mode: verify-full
   - Root Certificate: `~/.postgresql/root.crt`
   - Client Certificate: `~/.postgresql/DB_USER.crt`
   - Client Key: `~/.postgresql/DB_USER.key`

---

## 4. 커스텀 init.sql로 테이블 자동 생성

### 목적
PostgreSQL이 시작될 때 원하는 스키마와 테이블을 자동으로 생성하기 위함.

### 방법

1. `init.sql` 작성
```sql
-- init.sql 예시
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

2. PostgreSQL 서버에서 실행
```bash
sudo -u postgres psql -f /경로/init.sql
```

또는

3. PostgreSQL 컨테이너 사용 시 (Docker 예)
```dockerfile
COPY init.sql /docker-entrypoint-initdb.d/
```
컨테이너 시작 시 자동으로 실행됨.

---

## ✅ 참고
- `DB_USER`: 실제로는 PostgreSQL 유저명 (ex: `jinu`)
- `서버도메인`: `grapeman.duckdns.org` 등의 실제 서버 도메인 또는 IP
- 보안을 위해 PostgreSQL 외부 노출 시에는 반드시 SSL을 사용하고, 클라이언트 인증서를 통한 인증을 추천

