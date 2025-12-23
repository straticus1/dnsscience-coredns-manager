import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

export class DnsMigrate implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'DNS Migrate',
		name: 'dnsMigrate',
		icon: 'file:dnsmigrate.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["operation"]}}',
		description: 'Migrate between CoreDNS and Unbound',
		defaults: {
			name: 'DNS Migrate',
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
			// Operation
			{
				displayName: 'Operation',
				name: 'operation',
				type: 'options',
				noDataExpression: true,
				options: [
					{
						name: 'Plan',
						value: 'plan',
						description: 'Generate migration plan',
						action: 'Generate migration plan',
					},
					{
						name: 'Convert',
						value: 'convert',
						description: 'Convert configuration',
						action: 'Convert configuration',
					},
					{
						name: 'Validate',
						value: 'validate',
						description: 'Validate migration',
						action: 'Validate migration',
					},
					{
						name: 'Execute',
						value: 'execute',
						description: 'Execute migration',
						action: 'Execute migration',
					},
				],
				default: 'plan',
			},

			// Source resolver
			{
				displayName: 'Source',
				name: 'source',
				type: 'options',
				options: [
					{ name: 'CoreDNS', value: 'coredns' },
					{ name: 'Unbound', value: 'unbound' },
				],
				default: 'coredns',
				description: 'Source DNS resolver',
			},

			// Target resolver
			{
				displayName: 'Target',
				name: 'target',
				type: 'options',
				options: [
					{ name: 'CoreDNS', value: 'coredns' },
					{ name: 'Unbound', value: 'unbound' },
				],
				default: 'unbound',
				description: 'Target DNS resolver',
			},

			// Configuration for plan/convert
			{
				displayName: 'Configuration',
				name: 'config',
				type: 'string',
				typeOptions: {
					rows: 15,
				},
				displayOptions: {
					show: {
						operation: ['plan', 'convert'],
					},
				},
				default: '',
				required: true,
				description: 'Source configuration to migrate/convert',
			},

			// Domains for validate
			{
				displayName: 'Test Domains',
				name: 'domains',
				type: 'string',
				typeOptions: {
					rows: 5,
				},
				displayOptions: {
					show: {
						operation: ['validate'],
					},
				},
				default: 'google.com\ncloudflare.com\nexample.com',
				description: 'Domains to test during validation (one per line)',
			},

			// Dry run for execute
			{
				displayName: 'Dry Run',
				name: 'dryRun',
				type: 'boolean',
				displayOptions: {
					show: {
						operation: ['execute'],
					},
				},
				default: true,
				description: 'Whether to simulate without making changes',
			},

			// Migration plan for execute
			{
				displayName: 'Migration Plan',
				name: 'plan',
				type: 'json',
				displayOptions: {
					show: {
						operation: ['execute'],
					},
				},
				default: '{}',
				description: 'Migration plan from plan operation',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];
		const credentials = await this.getCredentials('dnsScienceApi');

		const operation = this.getNodeParameter('operation', 0) as string;
		const apiUrl = credentials.apiUrl as string;

		for (let i = 0; i < items.length; i++) {
			try {
				let endpoint = '';
				let method = 'POST';
				let body: any = {};

				const source = this.getNodeParameter('source', i) as string;
				const target = this.getNodeParameter('target', i) as string;

				if (operation === 'plan') {
					endpoint = '/api/v1/migrate/plan';
					body = {
						source,
						target,
						config: this.getNodeParameter('config', i) as string,
					};

				} else if (operation === 'convert') {
					endpoint = '/api/v1/migrate/convert';
					body = {
						source,
						target,
						config: this.getNodeParameter('config', i) as string,
					};

				} else if (operation === 'validate') {
					endpoint = '/api/v1/migrate/validate';
					const domainsText = this.getNodeParameter('domains', i) as string;
					const domains = domainsText.split('\n').map(d => d.trim()).filter(d => d);
					body = { domains };

				} else if (operation === 'execute') {
					endpoint = '/api/v1/migrate/execute';
					body = {
						plan: JSON.parse(this.getNodeParameter('plan', i) as string),
						dry_run: this.getNodeParameter('dryRun', i) as boolean,
					};
				}

				const options: any = {
					method,
					uri: `${apiUrl}${endpoint}`,
					body,
					json: true,
				};

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
