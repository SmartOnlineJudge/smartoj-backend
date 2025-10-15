# 智能算法刷题平台——后端仓库

## 快速开始

### 克隆仓库

```bash
git clone https://github.com/smartOnlineJudge/smartoj-backend
```

### 安装数据库

本项目涉及到的数据库有：

1. **MySQL**

   需要开启 binlog 日志。

2. **Redis**

3. **ElasticSearch**

   需要额外安装一个 IK 分词器插件。

4. **MinIO**

   这里需要注意是，安装好以后先创建一个桶用于存放用户的头像，代码不会自动创建桶。

   桶的名称是：`user-avatars`。如果需要修改桶的名称，可以修改`storage/oss.py`文件下的`AVATAR_BUCKET_NAME`常量的值。

   创建好桶以后，需要先上传一张默认的用户头像到这个桶上面。默认头像名称在`settings.py`中的`DEFAULT_USER_AVATAR`这个常量修改，当创建一个新用户的时候，会使用这个默认头像。

### 安装中间件

本项目需要用到 RabbitMQ 作为项目的消息队列。

### 添加 GitHub 代理

客户端的登录支持 GitHub OAuth2 登录，认证期间后端需要向 GitHub 发送请求，所以这个认证过程正常来说是不稳定的。这就会导致有时候会登录失败，因此需要使用一个代理来向 GitHub 发送请求。

在`settings.py`文件下，`PROXY_URL`这个常量就是代理的地址，默认使用的协议是`socks5`。同时也支持`socks4`、`HTTP`这些协议。

GitHub 相关的认证逻辑位于：`core/user/auth.py`下的`GithubOAuth2Authenticator`认证类。

### 修改项目配置文件

1. **metadata.json**

   项目最关键的配置文件，涉及到数据库、密钥、邮件、消息队列等服务的配置。

   其中 MySQL、Redis、ElasticSearch、MinIO、RabbitMQ 这些配置注意一下账号密码、URL 的值就行了。

   邮件发送的配置需要自己到 QQ 或者 163 上面申请一个 SMTP 的密钥，然后填写相关的配置就行了。

   这里主要说一下密钥的配置，也就是`secrets`这个配置。

   ```json
   "secrets": {
     "PASSWORD": "your_secret",
     "GITHUB_OAUTH2": {
       "client_id": "your client id",
       "client_secret": "your client secret"
     }
   }
   ```

   1. **PASSWORD**

      这个配置是用户密码加密的密钥，不管你的密钥是什么，最终都需要经过 base64 编码，才能写到这个配置文件上面，因为后端在读取这个密钥的时候，会先使用 base64 解码这个密钥。

      相关代码：`core/user/security.py/password_hash`、`core/user/auth.py/PasswordAuthenticator`。

   2. **GITHUB_OAUTH2**

      这个配置是用于 GitHub OAuth2 认证的，你需要先到 GitHub 中申请一个 GitHub OAuth APP。申请好以后它会提供相关的配置，将密钥填到配置文件上就行了。

2. **settings.py**

   首先，将`DEV_ENV`这个值改成 False。这个值会影响到核心配置文件的读取和数据库日志的输出。

   对于`API_DOCS_LOGO`这个常量，你可以改为空，也可以不改，但是现在的这个值使用的是第三方免费的图床，随时都有可能会失效。

   其他关键的配置在数据库安装那里已经做了相关说明了。

   剩下的配置基本上不用改就可以了。

### 启动项目

安装项目依赖，项目使用 UV 来管理第三方库，因此需要先安装好 UV，然后确保你的 Python 版本是 3.11。

运行以下命令来安装项目依赖：

```bash
uv sync
```

在启动后端之前，需要先将 MySQL 的部分数据迁移到 ElasticSearch 中，以实现全文检索功能。

在 scripts 目录下，有一个叫做`create_es_data.py`的脚本，你需要以模块的方式来运行这个 Python 文件。

```bash
uv run -m scripts.create_es_data
```

在 ElasticSearch 中查看是否有`question`这个索引结构，并查看这个索引里面是否有题目相关的数据，如果有数据，那么就代表数据迁移成功，可以进行下一步操作。

要想启动整个后端，除了前面说的数据库、中间件、消息队列以外，还需要启动 3 个进程。

1. Taskiq Worker

   这个 Worker 也相当于一个消息队列服务，底层用到同样是 RabbitMQ，只不过它让开发者们更多的关注业务层面的代码，而不是关注消息队列本身的代码。因此它相当于是 RabbtMQ 的代理人。

   通过以下命令来启动这个 Worker：
   ```bash
   uv run taskiq worker mq.broker:broker --workers 2
   ```

2. 后端服务

   ```bash
   uv run main.py
   ```

3. MySQL binlog 监听进程

   这个进程主要是监听 MySQL 数据的变化，然后将这些变化同时同步到 ElasticSearch 中。

   同样在`scripts`目录下，有一个名为`listen_mysql_binlog.py`的脚本，你需要以模块的方式来运行这个 Python 文件。

   ```bash
   uv run -m scripts.listen_mysql_binlog
   ```

   这个是一个长期运行的脚本，并且必须在消息队列和后端服务启动后，才可以启动这个进程。

由于整个后端需要启动的进程较多，因此推荐使用像 supervisor、docker 这样的进程管理工具来管理这些进程。