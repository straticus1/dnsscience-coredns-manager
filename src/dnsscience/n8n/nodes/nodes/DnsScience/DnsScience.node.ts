import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

export class DnsScience implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'DNS Science',
		name: 'dnsScience',
		icon: 'file:dnsscience.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"] + ": " + $parameter["resource"]}}',
		description: 'Manage CoreDNS and Unbound DNS resolvers',
		defaults: {
			name: 'DNS Science',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'dnsScienceApi',
				required: true,
			},
		],
		properties: [
			// Resource
			{
				displayName: 'Resource',
				name: 'resource',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Service',
						value: 'service',
						description: 'Manage DNS resolver service',
					},
					{
						name: 'Cache',
						value: 'cache',
						description: 'Manage DNS cache',
					},
					{
						name: 'Config',
						value: 'config',
						description: 'Manage configuration',
					},
					{
						name: 'Health',
						value: 'health',
						description: 'Health checks and metrics',
					},
				],
				default: 'service',
			},

			// Service Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['service'],
					},
				},
				options: [
					{
						name: 'Get Status',
						value: 'status',
						description: 'Get service status',
						action: 'Get service status',
					},
					{
						name: 'Start',
						value: 'start',
						description: 'Start the service',
						action: 'Start service',
					},
					{
						name: 'Stop',
						value: 'stop',
						description: 'Stop the service',
						action: 'Stop service',
					},
					{
						name: 'Restart',
						value: 'restart',
						description: 'Restart the service',
						action: 'Restart service',
					},
					{
						name: 'Reload',
						value: 'reload',
						description: 'Reload configuration',
						action: 'Reload configuration',
					},
				],
				default: 'status',
			},

			// Cache Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['cache'],
					},
				},
				options: [
					{
						name: 'Get Stats',
						value: 'stats',
						description: 'Get cache statistics',
						action: 'Get cache statistics',
					},
					{
						name: 'Flush',
						value: 'flush',
						description: 'Flush entire cache',
						action: 'Flush cache',
					},
					{
						name: 'Purge Domain',
						value: 'purge',
						description: 'Purge specific domain from cache',
						action: 'Purge domain from cache',
					},
				],
				default: 'stats',
			},

			// Cache Purge Domain
			{
				displayName: 'Domain',
				name: 'domain',
				type: 'string',
				displayOptions: {
					show: {
						resource: ['cache'],
						operation: ['purge'],
					},
				},
				default: '',
				required: true,
				description: 'Domain to purge from cache',
			},

			// Config Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['config'],
					},
				},
				options: [
					{
						name: 'Get',
						value: 'get',
						description: 'Get current configuration',
						action: 'Get configuration',
					},
					{
						name: 'Validate',
						value: 'validate',
						description: 'Validate configuration',
						action: 'Validate configuration',
					},
					{
						name: 'Apply',
						value: 'apply',
						description: 'Apply new configuration',
						action: 'Apply configuration',
					},
				],
				default: 'get',
			},

			// Config content for validate/apply
			{
				displayName: 'Configuration',
				name: 'config',
				type: 'string',
				typeOptions: {
					rows: 10,
				},
				displayOptions: {
					show: {
						resource: ['config'],
						operation: ['validate', 'apply'],
					},
				},
				default: '',
				description: 'Configuration content',
			},

			// Health Operations
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				displayOptions: {
					show: {
						resource: ['health'],
					},
				},
				options: [
					{
						name: 'Check',
						value: 'check',
						description: 'Perform health check',
						action: 'Health check',
					},
					{
						name: 'Metrics',
						value: 'metrics',
						description: 'Get Prometheus metrics',
						action: 'Get metrics',
					},
				],
				default: 'check',
			},

			// Resolver selection
			{
				displayName: 'Resolver',
				name: 'resolver',
				type: 'options',
				options: [
					{
						name: 'CoreDNS',
						value: 'coredns',
					},
					{
						name: 'Unbound',
						value: 'unbound',
					},
				],
				default: 'coredns',
				description: 'Target DNS resolver',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const credentials = await this.getCredentials('dnsScienceApi');

		const resource = this.getNodeParameter('resource', 0) as string;
		const operation = this.getNodeParameter('operation', 0) as string;
		const resolver = this.getNodeParameter('resolver', 0) as string;

		const apiUrl = credentials.apiUrl as string;

		for (let i = 0; i < items.length; i++) {
			try {
				let endpoint = '';
				let method = 'GET';
				let body = {};

				// Build request based on resource and operation
				if (resource === 'service') {
					if (operation === 'status') {
						endpoint = '/api/v1/service/status';
					} else {
						endpoint = `/api/v1/service/${operation}`;
						method = 'POST';
					}
				} else if (resource === 'cache') {
					if (operation === 'stats') {
						endpoint = '/api/v1/cache/stats';
					} else if (operation === 'flush') {
						endpoint = '/api/v1/cache';
						method = 'DELETE';
					} else if (operation === 'purge') {
						const domain = this.getNodeParameter('domain', i) as string;
						endpoint = `/api/v1/cache/${domain}`;
						method = 'DELETE';
					}
				} else if (resource === 'config') {
					if (operation === 'get') {
						endpoint = '/api/v1/config';
					} else if (operation === 'validate') {
						endpoint = '/api/v1/config/validate';
						method = 'POST';
						body = {
							config: this.getNodeParameter('config', i) as string,
							resolver: resolver,
						};
					} else if (operation === 'apply') {
						endpoint = '/api/v1/config/apply';
						method = 'POST';
						body = {
							config: this.getNodeParameter('config', i) as string,
							reload: true,
						};
					}
				} else if (resource === 'health') {
					if (operation === 'check') {
						endpoint = '/api/v1/health';
					} else if (operation === 'metrics') {
						endpoint = '/api/v1/health/metrics';
					}
				}

				// Make API request
				const options: any = {
					method,
					uri: `${apiUrl}${endpoint}`,
					json: true,
				};

				if (method === 'POST' && Object.keys(body).length > 0) {
					options.body = body;
				}

				if (credentials.apiKey) {
					options.headers = {
						'Authorization': `Bearer ${credentials.apiKey}`,
					};
				}

				const response = await this.helpers.request(options);

				returnData.push({
					json: response,
					pairedItem: { item: i },
				});

			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: { error: error.message },
						pairedItem: { item: i },
					});
					continue;
				}
				throw new NodeOperationError(this.getNode(), error, { itemIndex: i });
			}
		}

		return [returnData];
	}
}
