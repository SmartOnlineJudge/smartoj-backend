# 基于 ElasticSearch 官方镜像
FROM elasticsearch:8.18.4

# 安装 IK 分词器插件
RUN elasticsearch-plugin install --batch https://release.infinilabs.com/analysis-ik/stable/elasticsearch-analysis-ik-8.18.4.zip
